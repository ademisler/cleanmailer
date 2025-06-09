import json
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import pandas as pd

# Dış klasördeki .env dosyasını yükle
load_dotenv(dotenv_path="/etc/cleanmailer/.env")

ROOT = os.environ.get("CLEANMAILER_HOME", "/opt/cleanmailer")
MAIL_LIST_FILE = os.path.join(ROOT, "reports", "aktif_mailler.xlsx")
SENDERS_FILE = os.path.join(ROOT, "input", "Senders.xlsx")
TEMPLATE_FILE = os.path.join(ROOT, "templates", "mail_template.txt")
LOG_DIR = os.path.join(ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "send.log")
COUNTER_FILE = os.path.join(LOG_DIR, "daily_counter.json")
STATE_FILE = os.path.join(LOG_DIR, "smtp_state.json")

def main():
    os.makedirs(LOG_DIR, exist_ok=True)

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        mail_body = f.read()

    # Gönderici hesaplarını oku ve başlıkları normalize et
    df_senders = pd.read_excel(SENDERS_FILE)
    df_senders.columns = df_senders.columns.str.strip()
    df_senders = df_senders.rename(columns={
        "Mail": "Username",
        "Mdp": "Password",
        "SMTP Host": "SMTP",
        "SMTP Port": "Port",
        "Nom": "Name",
        "Günlük Limit": "DailyLimit",
    })

    # SMTP hesaplarını hazırla
    smtp_accounts = []
    for _, row in df_senders.iterrows():
        smtp_accounts.append(
            {
                "smtp_host": row["SMTP"],
                "smtp_port": row["Port"],
                "smtp_user": row["Username"],
                "smtp_pass": row["Password"],
                "from_name": row["Name"],
                "limit": int(row["DailyLimit"]),
            }
        )

    # Günlük sayaç dosyasını yükle veya başlat
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r") as f:
            counters_all = json.load(f)
    else:
        counters_all = {}

    if today not in counters_all:
        counters_all[today] = {}

    daily_counter = counters_all[today]

    # Hesap durumu dosyasını yükle
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            smtp_state = json.load(f)
    else:
        smtp_state = {}

    # Hedef listeyi yükle
    df_targets = pd.read_excel(MAIL_LIST_FILE)
    if "email" not in df_targets.columns:
        raise ValueError("Hedef listede 'email' sütunu bulunamadı.")

    recipients = df_targets["email"].dropna().tolist()
    recipient_batch = recipients[: len(smtp_accounts)]
    sent_count = 0

    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"\n--- Gönderim Başladı: {datetime.now()} ---\n")

        available_accounts = []
        for acc in smtp_accounts:
            if daily_counter.get(acc["smtp_user"], 0) >= acc["limit"]:
                continue
            state = smtp_state.get(acc["smtp_user"], {})
            paused_until = state.get("paused_until")
            if paused_until:
                try:
                    until = datetime.strptime(paused_until, "%Y-%m-%d")
                    if until > datetime.now():
                        continue
                    else:
                        state.pop("paused_until", None)
                        smtp_state[acc["smtp_user"]] = state
                except Exception:
                    pass
            available_accounts.append(acc)

        if not available_accounts:
            warning = "Uygun SMTP hesabı kalmadı. Gönderim durduruldu."
            print(warning)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.write(f"{ts} {warning}\n")
        else:
            for account, recipient in zip(available_accounts, recipient_batch):
                msg = MIMEMultipart()
                msg["From"] = f"{account['from_name']} <{account['smtp_user']}>"
                msg["To"] = recipient
                msg["Subject"] = "Potential Business Collaboration Inquiry"
                msg.attach(MIMEText(mail_body, "plain"))

                try:
                    with smtplib.SMTP_SSL(account["smtp_host"], int(account["smtp_port"])) as server:
                        server.login(account["smtp_user"], account["smtp_pass"])
                        server.sendmail(account["smtp_user"], recipient, msg.as_string())
                    status = f"[OK] {account['smtp_user']} -> {recipient}"
                    daily_counter[account["smtp_user"]] = daily_counter.get(account["smtp_user"], 0) + 1
                    sent_count += 1
                except Exception as e:
                    err = str(e)
                    if "spam" in err.lower():
                        state = smtp_state.setdefault(account["smtp_user"], {"spam_strikes": 0})
                        state["spam_strikes"] = state.get("spam_strikes", 0) + 1
                        pause_days = 7 if state["spam_strikes"] > 1 else 3
                        pause_until = (datetime.now() + timedelta(days=pause_days)).strftime("%Y-%m-%d")
                        state["paused_until"] = pause_until
                        smtp_state[account["smtp_user"]] = state
                        status = f"[FAIL] {account['smtp_user']} paused until {pause_until} : {err}"
                    else:
                        status = f"[ERROR] {account['smtp_user']} -> {recipient} : {err}"

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log.write(f"{timestamp} {status}\n")

            if len(available_accounts) < len(recipient_batch):
                warning = "Uygun SMTP hesabı kalmadı. Gönderim durduruldu."
                print(warning)
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log.write(f"{ts} {warning}\n")

            # işlenen alıcıları listeden çıkar ve kaydet
            if recipient_batch:
                df_targets.iloc[len(recipient_batch):].to_excel(MAIL_LIST_FILE, index=False)
                checked_dir = os.path.join(ROOT, "checked")
                os.makedirs(checked_dir, exist_ok=True)
                out_path = os.path.join(checked_dir, f"sent_{today}.xlsx")
                df_sent = pd.DataFrame({"email": recipient_batch})
                if os.path.exists(out_path):
                    prev = pd.read_excel(out_path)
                    df_sent = pd.concat([prev, df_sent], ignore_index=True)
                df_sent.to_excel(out_path, index=False)

        log.write(f"--- Gönderim Bitti: {datetime.now()} ---\n")

    # Sayaçları güncelle
    counters_all[today] = daily_counter
    with open(COUNTER_FILE, "w") as f:
        json.dump(counters_all, f, indent=2)
    with open(STATE_FILE, "w") as f:
        json.dump(smtp_state, f, indent=2)

    print(f"Toplam gönderilen e-posta: {sent_count}")


if __name__ == "__main__":
    main()
