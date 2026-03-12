import logging
import os
import smtplib
from email.message import EmailMessage


logger = logging.getLogger(__name__)


def _send_email(*, to_email: str, subject: str, body: str) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}

    logger.info(
        "Preparing email",
        extra={"to_email": to_email, "subject": subject, "smtp_host": smtp_host, "smtp_port": smtp_port, "smtp_use_tls": smtp_use_tls},
    )

    if not smtp_host or not smtp_from:
        logger.warning(
            "Skipping email because SMTP_HOST or SMTP_FROM is not configured",
            extra={"to_email": to_email, "smtp_host": smtp_host, "smtp_from_set": bool(smtp_from)},
        )
        return

    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if smtp_use_tls:
                logger.info("Starting TLS for SMTP connection")
                server.starttls()
            if smtp_user and smtp_password:
                logger.info("Authenticating with SMTP server", extra={"smtp_user": smtp_user})
                server.login(smtp_user, smtp_password)
            logger.info("Sending email", extra={"to_email": to_email, "subject": subject})
            server.send_message(message)
            logger.info("Email sent successfully", extra={"to_email": to_email, "subject": subject})
    except Exception:
        logger.exception("Failed to send email", extra={"to_email": to_email, "subject": subject, "smtp_host": smtp_host, "smtp_port": smtp_port})
        raise


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
