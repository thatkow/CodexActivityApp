import logging
import os
import smtplib
from email.message import EmailMessage


logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@example.com")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}
EMAIL_VERBOSE = os.getenv("EMAIL_VERBOSE", "true").lower() in {"1", "true", "yes", "on"}

if EMAIL_VERBOSE and not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _verbose(message: str) -> None:
    if EMAIL_VERBOSE:
        logger.info("[emails] %s", message)


def send_submission_notification(recipients: list[str], submission_id: int, submission_url: str) -> None:
    if not recipients:
        _verbose(f"Skipping submission #{submission_id}: no subscriber recipients configured.")
        return

    if not SMTP_HOST:
        _verbose(
            f"Skipping submission #{submission_id}: SMTP_HOST is not configured. "
            f"Would have notified: {', '.join(recipients)}"
        )
        return

    msg = EmailMessage()
    msg["Subject"] = f"New marker panel submission #{submission_id}"
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(recipients)
    msg.set_content(
        "A new marker panel has been submitted.\n\n"
        f"Submission: #{submission_id}\n"
        f"Open in admin panel: {submission_url}\n"
    )

    _verbose(
        f"Sending submission #{submission_id} email via {SMTP_HOST}:{SMTP_PORT} "
        f"to {len(recipients)} recipient(s): {', '.join(recipients)}"
    )
    _verbose(f"Email subject: {msg['Subject']}")
    _verbose(f"Email body:\n{msg.get_content()}")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_USE_TLS:
                _verbose("Starting TLS for SMTP connection.")
                server.starttls()
            if SMTP_USER:
                _verbose(f"Authenticating with SMTP username: {SMTP_USER}")
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as exc:
        logger.exception("[emails] Failed sending submission #%s notification: %s", submission_id, exc)
        return

    _verbose(f"Submission #{submission_id} notification sent successfully.")
