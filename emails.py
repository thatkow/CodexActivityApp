import os
import smtplib
from email.message import EmailMessage


def _send_email(*, to_email: str, subject: str, body: str) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}

    if not smtp_host or not smtp_from:
        return

    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        if smtp_use_tls:
            server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.send_message(message)


def send_project_member_added_email(
    *,
    to_email: str,
    member_name: str,
    project_name: str,
    organization_name: str | None,
    project_url: str,
) -> None:
    subject = f"Assigned to project: {project_name}"
    org_line = f"Organization: {organization_name}\n" if organization_name else ""
    body = (
        f"Hello {member_name},\n\n"
        f"You have been added to the project '{project_name}'.\n"
        f"{org_line}"
        f"Project link: {project_url}\n\n"
        "This is an automated notification from CodexActivityApp."
    )
    _send_email(to_email=to_email, subject=subject, body=body)


def send_project_member_removed_email(
    *,
    to_email: str,
    member_name: str,
    project_name: str,
    organization_name: str | None,
    project_url: str,
) -> None:
    subject = f"Removed from project: {project_name}"
    org_line = f"Organization: {organization_name}\n" if organization_name else ""
    body = (
        f"Hello {member_name},\n\n"
        f"You have been removed from the project '{project_name}'.\n"
        f"{org_line}"
        f"Project link: {project_url}\n\n"
        "This is an automated notification from CodexActivityApp."
    )
    _send_email(to_email=to_email, subject=subject, body=body)
