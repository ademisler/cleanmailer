import imaplib
import logging
import os
import re
import email
import pandas as pd
from email.header import decode_header
from email.utils import parseaddr
import unicodedata

ROOT = os.environ.get("CLEANMAILER_HOME", "/opt/cleanmailer")
LOG_DIR = os.path.join(ROOT, "logs")
SENDERS_FILE = os.path.join(ROOT, "input", "Senders.xlsx")
BOUNCE_FILE = os.path.join(ROOT, "reports", "bounced.xlsx")
REPLY_FILE = os.path.join(ROOT, "reports", "replied.xlsx")

def normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    return text.lower().replace(".", "").replace(" ", "")

def decode_mime_words(text: str) -> str:
    try:
        decoded = decode_header(text)
        return "".join(
            str(part[0], part[1] or "utf-8") if isinstance(part[0], bytes) else str(part[0])
            for part in decoded
        )
    except Exception:
        return text

LOG_FILE = os.path.join(LOG_DIR, "feedback.log")

def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(BOUNCE_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(REPLY_FILE), exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == LOG_FILE for h in logger.handlers):
        handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(handler)

    logger.info("Feedback check started")

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
            logger.warning("Eksik IMAP bilgisi: %s", imap_user)
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
                folder_norm = normalize(folder_name)

                logger.info("Denenen klasör: %s", folder_name)

                try:
                    status, _ = mail.select(folder_name)
                    if status != "OK":
                        logger.info("%s klasör atlandı (%s)", imap_user, folder_name)
                        continue

                    status, messages = mail.search(None, "ALL")
                    mail_ids = messages[0].split()
                    logger.debug("%s klasör: %s -> %d", imap_user, folder_name, len(mail_ids))

                    for num in mail_ids[::-1]:
                        status, msg_data = mail.fetch(num, "(RFC822)")
                        if status != "OK":
                            logger.warning("Fetch failed for %s msg %s: %s", folder_name, num, status)
                            continue
                        for response_part in msg_data:
                            if not isinstance(response_part, tuple):
                                continue
                            try:
                                msg = email.message_from_bytes(response_part[1])
                                subject = decode_mime_words(msg.get("Subject", ""))
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
                                            except Exception as e:
                                                logger.exception("Payload decode failed for %s msg %s: %s", folder_name, num, e)
                                                continue
                                    if not real_target:
                                        real_target = "UNKNOWN"

                                    logger.info("Bounced detected: %s | Subject=%s", real_target, subject)
                                    all_bounced.append({"email": real_target, "subject": subject})

                                elif "auto-reply" in subject.lower():
                                    continue
                                elif (
                                    "re:" in subject.lower()
                                    or "reply" in subject.lower()
                                    or "ynt:" in subject.lower()
                                    or msg.get("In-Reply-To")
                                    or msg.get("References")
                                ):
                                    logger.info("Reply detected: %s | Subject=%s", real_email, subject)
                                    all_replied.append({"email": real_email, "subject": subject})
                                else:
                                    logger.info("Mail REPLY olarak işlenmedi: From=%s | Subject=%s", real_email, subject)
                            except Exception as e:
                                logger.exception("Message parsing failed for %s msg %s: %s", folder_name, num, e)
                                continue

                except Exception as e:
                    logger.warning("%s klasör işlenemedi (%s): %s", imap_user, folder_name, e)

            mail.logout()

        except Exception as e:
            logger.error("IMAP erişimi başarısız (%s): %s", imap_user, e)

    if all_bounced:
        pd.DataFrame(all_bounced).to_excel(BOUNCE_FILE, index=False)

    if all_replied:
        pd.DataFrame(all_replied).to_excel(REPLY_FILE, index=False)

    logger.info("Script completed. Bounced: %d, Replied: %d", len(all_bounced), len(all_replied))
    print(f"Toplam bounced: {len(all_bounced)} | replied: {len(all_replied)}")

if __name__ == "__main__":
    main()
