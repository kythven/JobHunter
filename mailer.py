"""Send the daily digest by email via Gmail SMTP."""
import os
import smtplib
import sys
from email.mime.text import MIMEText

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
DIGEST_TO = os.environ.get("DIGEST_TO")


def send_digest_email(subject: str, body: str):
    if not (GMAIL_ADDRESS and GMAIL_APP_PASSWORD and DIGEST_TO):
        print("[mailer] GMAIL_ADDRESS/GMAIL_APP_PASSWORD/DIGEST_TO not all set, skipping email.",
              file=sys.stderr)
        return

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = DIGEST_TO

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, [DIGEST_TO], msg.as_string())
        print(f"[mailer] Digest emailed to {DIGEST_TO}")
    except smtplib.SMTPException as e:
        print(f"[mailer] Failed to send digest email: {e}", file=sys.stderr)
