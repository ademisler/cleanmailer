import imaplib
import email
import pandas as pd
import re
import os
from email.header import decode_header
from email.utils import parseaddr
from imapclient import imap_utf7

# 🔧 Dosya yolları
ROOT = os.environ.get("MAIL_OTO_HOME", "/opt/mail_oto")
SENDERS_FILE = os.path.join(ROOT, "input", "Senders.xlsx")
TEST_BOUNCE = os.path.join(ROOT, "reports", "test_bounced.xlsx")
TEST_REPLY = os.path.join(ROOT, "reports", "test_replied.xlsx")

# Sonuç listeleri
all_bounced = []
all_replied = []

# Hesapları oku
df_accounts = pd.read_excel(SENDERS_FILE)
df_accounts.columns = df_accounts.columns.str.strip()

for _, row in df_accounts.iterrows():
    imap_host = row.get("IMAP Host")
    imap_port = int(row.get("IMAP Port", 993))
    imap_user = row.get("Mail")
    imap_pass = row.get("Mdp")

    print(f"\n--- TEST: {imap_user} ---")

    if not all([imap_host, imap_user, imap_pass]):
        print(f"[SKIP] Eksik IMAP bilgisi: {imap_user}")
        continue

    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(imap_user, imap_pass)

        typ, folders = mail.list()
        print(f"[INFO] {len(folders)} klasör bulundu")

        for folder in folders:
            decoded = folder.decode()
            match = re.search(r'".*" "(.*)"', decoded)
            if not match:
                continue

            folder_name = match.group(1)
            folder_key = folder_name.lower()
            if not any(k in folder_key for k in ["inbox", "spam", "junk", "trash"]):
                print(f"[SKIP] {folder_name}")
                continue

            utf7_folder = imap_utf7.encode(folder_name)
            status, _ = mail.select(utf7_folder)
            if status != 'OK':
                print(f"[SKIP] klasör atlandı ({folder_name})")
                continue

            status, messages = mail.search(None, "ALL")
            mail_ids = messages[0].split()
            print(f"[INFO] {folder_name}: {len(mail_ids)} mail bulundu")

            for num in mail_ids[::-1]:
                status, msg_data = mail.fetch(num, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject_raw, encoding = decode_header(msg.get("Subject", ""))[0]
                        subject = subject_raw.decode(encoding or "utf-8") if isinstance(subject_raw, bytes) else subject_raw
                        from_email = msg.get("From", "")
                        real_email = parseaddr(from_email)[1]

                        print(f"   - From: {real_email} | Subject: {subject}")

                        if "mailer-daemon" in from_email.lower() or "postmaster@" in from_email.lower():
                            real_target = None
                            if msg.is_multipart():
                                for part in msg.walk():
                                    try:
                                        text = part.get_payload(decode=True).decode(errors="ignore")
                                        for line in text.splitlines():
                                            if "Final-Recipient" in line or "Original-Recipient" in line:
                                                if ";" in line:
                                                    real_target = line.split(";")[-1].strip()
                                                    break
                                            elif line.lower().startswith("to:"):
                                                real_target = line.split(":")[-1].strip()
                                                break
                                    except:
                                        continue
                            if not real_target:
                                real_target = "UNKNOWN"
                            all_bounced.append({"email": real_target, "subject": subject})
                        elif "auto-reply" in subject.lower():
                            continue
                        else:
                            all_replied.append({"email": real_email, "subject": subject})

        mail.logout()

    except Exception as e:
        print(f"[ERROR] IMAP bağlantısı başarısız ({imap_user}): {e}")

# Sonuçları kaydet
if all_bounced:
    pd.DataFrame(all_bounced).to_excel(TEST_BOUNCE, index=False)
    print(f"[DONE] test_bounced.xlsx oluşturuldu ({len(all_bounced)} satır)")

if all_replied:
    pd.DataFrame(all_replied).to_excel(TEST_REPLY, index=False)
    print(f"[DONE] test_replied.xlsx oluşturuldu ({len(all_replied)} satır)")
