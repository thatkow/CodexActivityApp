import os
import smtplib
from email.message import EmailMessage


def _to_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def send_project_membership_email(
    *,
    member_email: str,
    member_full_name: str,
    project_name: str,
    project_id: int,
    action: str,
) -> bool:
    """Send project membership add/remove email. Returns True on success."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM") or smtp_user
    use_tls = _to_bool(os.getenv("SMTP_USE_TLS"), True)
    app_base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    if not smtp_host or not smtp_from:
        return False

    action_text = "added to" if action == "added" else "removed from"
    project_url = f"{app_base_url}/projects/{project_id}"

    message = EmailMessage()
    message["Subject"] = f"Project membership update: {project_name}"
    message["From"] = smtp_from
    message["To"] = member_email
    message.set_content(
        f"Hello {member_full_name},\n\n"
        f"You have been {action_text} project '{project_name}'.\n"
        f"Project link: {project_url}\n\n"
        "Regards,\nCodexActivityApp"
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if use_tls:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(message)
        return True
    except Exception:
        return False
