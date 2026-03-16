import logging
import os
import smtplib
from email.message import EmailMessage


logger = logging.getLogger(__name__)


def _to_bool(value: str, default: bool) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _get_smtp_settings() -> dict[str, str | int | bool]:
    smtp_port_raw = os.getenv("SMTP_PORT", "587")
    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        smtp_port = 587

    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": smtp_port,
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_email": os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "") or "no-reply@example.com"),
        "use_tls": _to_bool(os.getenv("SMTP_USE_TLS", "true"), True),
        "verbose": _to_bool(os.getenv("EMAIL_VERBOSE", "true"), True),
    }


def _verbose(enabled: bool, message: str) -> None:
    if enabled:
        logger.info("[emails] %s", message)


def send_submission_notification(recipients: list[str], submission_id: int, submission_url: str) -> None:
    settings = _get_smtp_settings()
    verbose = bool(settings["verbose"])

    if verbose and not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not recipients:
        _verbose(verbose, f"Skipping submission #{submission_id}: no subscriber recipients configured.")
        return

    smtp_host = str(settings["host"])
    smtp_port = int(settings["port"])
    smtp_user = str(settings["user"])
    smtp_password = str(settings["password"])
    smtp_from = str(settings["from_email"])
    smtp_use_tls = bool(settings["use_tls"])

    if not smtp_host:
        _verbose(
            verbose,
            f"Skipping submission #{submission_id}: SMTP_HOST is not configured. "
            f"Would have notified: {', '.join(recipients)}",
        )
        return

    msg = EmailMessage()
    msg["Subject"] = f"New marker panel submission #{submission_id}"
    msg["From"] = smtp_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(
        "A new marker panel has been submitted.\n\n"
        f"Submission: #{submission_id}\n"
        f"Open in admin panel: {submission_url}\n"
    )

    _verbose(
        verbose,
        f"Sending submission #{submission_id} email via {smtp_host}:{smtp_port} "
        f"to {len(recipients)} recipient(s): {', '.join(recipients)}",
    )
    _verbose(verbose, f"Email subject: {msg['Subject']}")
    _verbose(verbose, f"Email body:\n{msg.get_content()}")

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if smtp_use_tls:
                _verbose(verbose, "Starting TLS for SMTP connection.")
                server.starttls()
            if smtp_user:
                _verbose(verbose, f"Authenticating with SMTP username: {smtp_user}")
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as exc:
        logger.exception("[emails] Failed sending submission #%s notification: %s", submission_id, exc)
        return

    _verbose(verbose, f"Submission #{submission_id} notification sent successfully.")
