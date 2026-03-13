import smtplib
from email.message import EmailMessage
from typing import Iterable


def send_submission_notification(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    smtp_use_tls: bool,
    sender_email: str,
    recipients: Iterable[str],
    submission_id: int,
    submission_url: str,
) -> None:
    recipient_list = [email.strip() for email in recipients if email and email.strip()]
    if not recipient_list:
        return

    message = EmailMessage()
    message["Subject"] = f"New Marker Panel Submission #{submission_id}"
    message["From"] = sender_email
    message["To"] = ", ".join(recipient_list)
    message.set_content(
        "A new marker panel submission is available for review.\n\n"
        f"Submission ID: {submission_id}\n"
        f"Review page: {submission_url}\n"
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        if smtp_use_tls:
            server.starttls()
        if smtp_username:
            server.login(smtp_username, smtp_password)
        server.send_message(message)
