
import imaplib
import email
import pandas as pd
from email.header import decode_header
from email.utils import parseaddr
import re
from imapclient import imap_utf7

SENDERS_FILE = "/opt/mail_oto/input/Senders.xlsx"
BOUNCE_FILE = "/opt/mail_oto/reports/bounced.xlsx"
REPLY_FILE = "/opt/mail_oto/reports/replied.xlsx"

all_bounced = []
all_replied = []

df_accounts = pd.read_excel(SENDERS_FILE)
df_accounts.columns = df_accounts.columns.str.strip()

for _, row in df_accounts.iterrows():
    imap_host = row.get("IMAP Host")
    imap_port = int(row.get("IMAP Port", 993))
    imap_user = row.get("Mail")
    imap_pass = row.get("Mdp")

    if not all([imap_host, imap_user, imap_pass]):
        print(f"[SKIP] Eksik IMAP bilgisi: {imap_user}")
        continue

    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(imap_user, imap_pass)

        typ, folders = mail.list()

        for folder in folders:
            decoded = folder.decode()
            match = re.search(r'".*" "(.*)"', decoded)
            if not match:
                continue

            folder_name = match.group(1)
            folder_key = folder_name.lower()

            if not any(k in folder_key for k in ["inbox", "spam", "junk", "trash"]):
                continue

            utf7_folder = imap_utf7.encode(folder_name)

            try:
                status, _ = mail.select(utf7_folder)
                if status != 'OK':
                    print(f"[SKIP] {imap_user} klasör atlandı ({folder_name})")
                    continue

                status, messages = mail.search(None, "ALL")
                mail_ids = messages[0].split()
                print(f"[DEBUG] {imap_user} klasör: {folder_name} → Mail sayısı: {len(mail_ids)}")

                for num in mail_ids[::-1]:
                    status, msg_data = mail.fetch(num, "(RFC822)")
                    print(f"[DEBUG] fetch result ({num}): {status}, data length: {len(msg_data)}")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            subject, encoding = decode_header(msg["Subject"])[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding or "utf-8", errors="ignore")

                            from_email = msg.get("From", "")
                            real_email = parseaddr(from_email)[1]

                            print(f"[DEBUG] From: {real_email} | Subject: {subject}")

                            if "mailer-daemon" in from_email.lower() or "postmaster@" in from_email.lower():
                                real_target = None
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        try:
                                            payload = part.get_payload(decode=True)
                                            if payload:
                                                text = payload.decode(errors="ignore")
                                                if "Final-Recipient" in text:
                                                    for line in text.splitlines():
                                                        if "Final-Recipient" in line or "Original-Recipient" in line:
                                                            if ";" in line:
                                                                real_target = line.split(";")[-1].strip()
                                                                break
                                                elif "To:" in text:
                                                    for line in text.splitlines():
                                                        if line.lower().startswith("to:"):
                                                            real_target = line.split(":")[-1].strip()
                                                            break
                                        except Exception:
                                            continue
                                if not real_target:
                                    real_target = "UNKNOWN"
                                all_bounced.append({"email": real_target, "subject": subject})

                            elif "auto-reply" in subject.lower():
                                continue
                            else:
                                all_replied.append({"email": real_email, "subject": subject})

            except Exception as e:
                print(f"[WARN] {imap_user} klasör işlenemedi ({folder_name}): {e}")

        mail.logout()

    except Exception as e:
        print(f"[ERROR] IMAP erişimi başarısız ({imap_user}): {e}")

if all_bounced:
    pd.DataFrame(all_bounced).to_excel(BOUNCE_FILE, index=False)

if all_replied:
    pd.DataFrame(all_replied).to_excel(REPLY_FILE, index=False)

print(f"Toplam bounced: {len(all_bounced)} | replied: {len(all_replied)}")
