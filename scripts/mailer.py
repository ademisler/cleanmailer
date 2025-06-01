import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

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
