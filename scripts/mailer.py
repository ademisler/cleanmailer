import argparse
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_report(subject, body, attachments=None):
    sender_email = os.environ.get("SMTP_SENDER")
    receiver_email = os.environ.get("SMTP_RECEIVER")
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", 465))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    required = {
        "SMTP_SENDER": sender_email,
        "SMTP_RECEIVER": receiver_email,
        "SMTP_SERVER": smtp_server,
        "SMTP_USER": smtp_user,
        "SMTP_PASS": smtp_pass,
    }
    missing = [name for name, val in required.items() if not val]
    if missing:
        raise EnvironmentError(
            "Missing required SMTP environment variables: " + ", ".join(missing)
        )

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachments:
        for path in attachments:
            with open(path, "rb") as f:
                filename = os.path.basename(path)
                part = MIMEApplication(f.read(), Name=filename)
                part['Content-Disposition'] = f'attachment; filename="{filename}"'
                msg.attach(part)

    if smtp_port == 465:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)  # ✅ BU KISIM EN KRİTİK
    else:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()

    server.login(smtp_user, smtp_pass)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()


def main():
    parser = argparse.ArgumentParser(description="Send a report email")
    parser.add_argument("-s", "--subject", default="CleanMailer Report",
                        help="Email subject")
    parser.add_argument("-b", "--body", default="See attachments for details.",
                        help="Email body")
    parser.add_argument("attachments", nargs="*", help="Files to attach")
    args = parser.parse_args()

    # If no attachments are given explicitly, attach the default report if it exists
    if not args.attachments:
        default_path = "/opt/cleanmailer/reports/temiz_liste_final.xlsx"
        if os.path.exists(default_path):
            args.attachments = [default_path]
        else:
            args.attachments = []

    send_report(args.subject, args.body, args.attachments)


if __name__ == "__main__":
    main()
