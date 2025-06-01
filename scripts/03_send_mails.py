import pandas as pd
import smtplib
import time
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Dosya yolları
ROOT = os.environ.get("MAIL_OTO_HOME", "/opt/mail_oto")
MAIL_LIST_FILE = os.path.join(ROOT, "reports", "aktif_mailler.xlsx")
SENDERS_FILE = os.path.join(ROOT, "input", "Senders.xlsx")
TEMPLATE_FILE = os.path.join(ROOT, "templates", "mail_template.txt")
LOG_FILE = os.path.join(ROOT, "logs", "send.log")
COUNTER_FILE = os.path.join(ROOT, "logs", "daily_counter.json")

# Mail içeriğini oku
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
    "Günlük Limit": "DailyLimit"
})

# SMTP hesaplarını hazırla
smtp_accounts = []
for _, row in df_senders.iterrows():
    smtp_accounts.append({
        "smtp_host": row["SMTP"],
        "smtp_port": row["Port"],
        "smtp_user": row["Username"],
        "smtp_pass": row["Password"],
        "from_name": row["Name"],
        "limit": int(row["DailyLimit"])
    })

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
sent_count = 0

with open(LOG_FILE, "a", encoding="utf-8") as log:
    log.write(f"\n--- Gönderim Başladı: {datetime.now()} ---\n")

    for index, row in df_targets.iterrows():
        recipient = row["email"]

        # Uygun bir SMTP hesabı bul
        sender = None
        for account in smtp_accounts:
            email = account["smtp_user"]
            used = daily_counter.get(email, 0)
            if used < account["limit"]:
                sender = account
                break

        if not sender:
            print("Uygun SMTP hesabı kalmadı. Gönderim durduruldu.")
            break

        # Mail oluştur
        msg = MIMEMultipart()
        msg["From"] = f"{sender['from_name']} <{sender['smtp_user']}>"
        msg["To"] = recipient
        msg["Subject"] = "Potential Business Collaboration Inquiry"
        msg.attach(MIMEText(mail_body, "plain"))

        try:
            server = smtplib.SMTP_SSL(sender["smtp_host"], int(sender["smtp_port"]))
            server.login(sender["smtp_user"], sender["smtp_pass"])
            server.sendmail(sender["smtp_user"], recipient, msg.as_string())
            server.quit()
            status = f"[OK] {recipient} - {sender['smtp_user']}"
            daily_counter[sender["smtp_user"]] = daily_counter.get(sender["smtp_user"], 0) + 1
            sent_count += 1
        except Exception as e:
            status = f"[ERROR] {recipient} - {str(e)}"

        # Log yaz
        log.write(status + "\n")

    log.write(f"--- Gönderim Bitti: {datetime.now()} ---\n")

# Sayaçları güncelle
counters_all[today] = daily_counter
with open(COUNTER_FILE, "w") as f:
    json.dump(counters_all, f, indent=2)

print(f"Toplam gönderilen e-posta: {sent_count}")

