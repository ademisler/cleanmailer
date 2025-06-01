
import pandas as pd
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from datetime import datetime
import os

ROOT = os.environ.get("MAIL_OTO_HOME", "/opt/mail_oto")
SENDERS_FILE = os.path.join(ROOT, "input", "Senders.xlsx")
LOG_FILE = os.path.join(ROOT, "logs", "account_test.log")

df = pd.read_excel(SENDERS_FILE)
df.columns = df.columns.str.strip()

summary = []

for _, row in df.iterrows():
    smtp_user = row.get("Mail")
    smtp_pass = row.get("Mdp")
    smtp_host = row.get("SMTP Host")
    smtp_port = int(row.get("SMTP Port", 465))
    imap_host = row.get("IMAP Host")
    imap_port = int(row.get("IMAP Port", 993))

    smtp_status = "UNKNOWN"
    imap_status = "UNKNOWN"

    # SMTP Testi
    try:
        msg = MIMEText("SMTP test maili - " + str(datetime.now()))
        msg["Subject"] = "SMTP Test"
        msg["From"] = smtp_user
        msg["To"] = smtp_user  # Kendine gönderim

        server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, smtp_user, msg.as_string())
        server.quit()
        smtp_status = "OK"
    except Exception as e:
        smtp_status = f"FAIL ({str(e)})"

    # IMAP Testi
    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(smtp_user, smtp_pass)
        mail.select("INBOX")
        status, messages = mail.search(None, "ALL")
        mail_ids = messages[0].split()
        imap_status = f"OK ({len(mail_ids)} mail)"
        mail.logout()
    except Exception as e:
        imap_status = f"FAIL ({str(e)})"

    line = f"{smtp_user} | SMTP: {smtp_status} | IMAP: {imap_status}"
    print(line)
    summary.append(line)

# Log dosyasına yaz
with open(LOG_FILE, "a", encoding="utf-8") as f:
    f.write("\n--- Hesap Testi: " + str(datetime.now()) + " ---\n")
    for line in summary:
        f.write(line + "\n")

print("\nTüm hesaplar test edildi. Log: " + LOG_FILE)
