
import imaplib
import logging
import os
import re
import email
import pandas as pd
from email.header import decode_header
from email.utils import parseaddr
from imapclient import imap_utf7

ROOT = os.environ.get("CLEANMAILER_HOME", "/opt/cleanmailer")
LOG_DIR = os.path.join(ROOT, "logs")
SENDERS_FILE = os.path.join(ROOT, "input", "Senders.xlsx")
BOUNCE_FILE = os.path.join(ROOT, "reports", "bounced.xlsx")
REPLY_FILE = os.path.join(ROOT, "reports", "replied.xlsx")

def main():
    logging.basicConfig(
        filename=os.path.join(LOG_DIR, "feedback.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    os.makedirs(LOG_DIR, exist_ok=True)

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
            logging.warning("Eksik IMAP bilgisi: %s", imap_user)
            continue

        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port)
            mail.login(imap_user, imap_pass)

            _, folders = mail.list()

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
                    if status != "OK":
                        logging.info("%s klasör atlandı (%s)", imap_user, folder_name)
                        continue

                    status, messages = mail.search(None, "ALL")
                    mail_ids = messages[0].split()
                    logging.debug("%s klasör: %s -> %d", imap_user, folder_name, len(mail_ids))

                    for num in mail_ids[::-1]:
                        status, msg_data = mail.fetch(num, "(RFC822)")
                        logging.debug("fetch result (%s): %s", num, status)
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                subject, encoding = decode_header(msg["Subject"])[0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode(encoding or "utf-8", errors="ignore")

                                from_email = msg.get("From", "")
                                real_email = parseaddr(from_email)[1]

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
elif "re:" in subject.lower() or "reply" in subject.lower():
    all_replied.append({"email": real_email, "subject": subject})
else:
    logging.info("Mail REPLY olarak işlenmedi: From=%s | Subject=%s", real_email, subject)


                except Exception as e:
                    logging.warning("%s klasör işlenemedi (%s): %s", imap_user, folder_name, e)

            mail.logout()

        except Exception as e:
            logging.error("IMAP erişimi başarısız (%s): %s", imap_user, e)

    if all_bounced:
        pd.DataFrame(all_bounced).to_excel(BOUNCE_FILE, index=False)

    if all_replied:
        pd.DataFrame(all_replied).to_excel(REPLY_FILE, index=False)

    print(f"Toplam bounced: {len(all_bounced)} | replied: {len(all_replied)}")


if __name__ == "__main__":
    main()
