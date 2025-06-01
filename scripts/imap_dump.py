
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr

# Hedef hesap bilgileri (şifreyi elle doldur!)
IMAP_HOST = "mail-fr.securemail.pro"
IMAP_PORT = 993
EMAIL_USER = "liora@mercufra.com"
EMAIL_PASS = "Pass323423@DSV"  # ← buraya şifreyi yaz

def decode_mime_words(s):
    try:
        decoded = decode_header(s)
        return ''.join(
            str(part[0], part[1] or 'utf-8') if isinstance(part[0], bytes) else str(part[0])
            for part in decoded
        )
    except Exception:
        return s

def main():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")

        status, messages = mail.search(None, "ALL")
        mail_ids = messages[0].split()
        print(f"Toplam mesaj: {len(mail_ids)}")

        for num in mail_ids[-10:]:  # Son 10 maili getir
            status, msg_data = mail.fetch(num, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_mime_words(msg.get("Subject", ""))
                    from_email = parseaddr(msg.get("From", ""))[1]

                    print("=" * 50)
                    print(f"From: {from_email}")
                    print(f"Subject: {subject}")

                    # Body içeriği
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                body = part.get_payload(decode=True)
                                if body:
                                    print(f"Body (ilk 200 karakter):\n{body[:200].decode(errors='ignore')}")
                                    break
                    else:
                        body = msg.get_payload(decode=True)
                        if body:
                            print(f"Body (ilk 200 karakter):\n{body[:200].decode(errors='ignore')}")

        mail.logout()

    except Exception as e:
        print(f"[HATA] IMAP erişimi başarısız: {e}")

if __name__ == "__main__":
    main()
