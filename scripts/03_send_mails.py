import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

ROOT = os.environ.get("CLEANMAILER_HOME", "/opt/cleanmailer")
MAIL_LIST_FILE = os.path.join(ROOT, "reports", "aktif_mailler.xlsx")
SENDERS_FILE = os.path.join(ROOT, "input", "Senders.xlsx")
TEMPLATE_FILE = os.path.join(ROOT, "templates", "mail_template.txt")
LOG_DIR = os.path.join(ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "send.log")
COUNTER_FILE = os.path.join(LOG_DIR, "daily_counter.json")

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

# Hedef listeyi yükle
    df_targets = pd.read_excel(MAIL_LIST_FILE)
    if "email" not in df_targets.columns:
        raise ValueError("Hedef listede 'email' sütunu bulunamadı.")

    recipients = df_targets["email"].dropna().tolist()
    sent_count = 0

    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"\n--- Gönderim Başladı: {datetime.now()} ---\n")

        available_accounts = [
            acc for acc in smtp_accounts
            if daily_counter.get(acc["smtp_user"], 0) < acc["limit"]
        ]

        if not available_accounts:
            warning = "Uygun SMTP hesabı kalmadı. Gönderim durduruldu."
            print(warning)
            log.write(warning + "\n")
        else:
            for account, recipient in zip(available_accounts, recipients):
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
                    status = f"[ERROR] {account['smtp_user']} -> {recipient} : {str(e)}"

                log.write(status + "\n")

            if len(available_accounts) < len(recipients):
                warning = "Uygun SMTP hesabı kalmadı. Gönderim durduruldu."
                print(warning)
                log.write(warning + "\n")

        log.write(f"--- Gönderim Bitti: {datetime.now()} ---\n")

# Sayaçları güncelle
    counters_all[today] = daily_counter
    with open(COUNTER_FILE, "w") as f:
        json.dump(counters_all, f, indent=2)

    print(f"Toplam gönderilen e-posta: {sent_count}")


if __name__ == "__main__":
    main()

