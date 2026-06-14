import logging
from typing import Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

EMAIL_TEMPLATES_DIR = Path(__file__).parent.parent / "email_templates"

jinja_env = Environment(
    loader=FileSystemLoader(str(EMAIL_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _get_mail_config() -> Optional[ConnectionConfig]:
    if not settings.MAIL_ENABLED or not settings.SMTP_USER:
        return None
    return ConnectionConfig(
        MAIL_USERNAME=settings.SMTP_USER,
        MAIL_PASSWORD=settings.SMTP_PASSWORD,
        MAIL_FROM=settings.EMAILS_FROM_EMAIL,
        MAIL_PORT=settings.SMTP_PORT,
        MAIL_SERVER=settings.SMTP_HOST,
        MAIL_FROM_NAME=settings.EMAILS_FROM_NAME,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
    )


async def send_booking_confirmation_guest(
    guest_email: str,
    guest_name: str,
    owner_name: str,
    start_datetime: str,
    end_datetime: str,
    meeting_notes: Optional[str] = None,
):
    """Send confirmation email to the guest."""
    conf = _get_mail_config()
    if not conf:
        logger.info(f"[EMAIL MOCK] Confirmation to guest {guest_email} — mail disabled")
        return

    template = jinja_env.get_template("booking_guest.html")
    body = template.render(
        guest_name=guest_name,
        owner_name=owner_name,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        meeting_notes=meeting_notes,
        app_name=settings.EMAILS_FROM_NAME,
    )

    message = MessageSchema(
        subject=f"✅ Reunião confirmada com {owner_name}",
        recipients=[guest_email],
        body=body,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        logger.info(f"Confirmation email sent to guest: {guest_email}")
    except Exception as e:
        logger.error(f"Failed to send guest email: {e}")


async def send_booking_notification_owner(
    owner_email: str,
    owner_name: str,
    guest_name: str,
    guest_email: str,
    guest_notes: Optional[str],
    start_datetime: str,
    end_datetime: str,
):
    """Send new booking notification to the calendar owner."""
    conf = _get_mail_config()
    if not conf:
        logger.info(f"[EMAIL MOCK] Notification to owner {owner_email} — mail disabled")
        return

    template = jinja_env.get_template("booking_owner.html")
    body = template.render(
        owner_name=owner_name,
        guest_name=guest_name,
        guest_email=guest_email,
        guest_notes=guest_notes,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        app_name=settings.EMAILS_FROM_NAME,
    )

    message = MessageSchema(
        subject=f"📅 Nova reunião agendada com {guest_name}",
        recipients=[owner_email],
        body=body,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        logger.info(f"Notification email sent to owner: {owner_email}")
    except Exception as e:
        logger.error(f"Failed to send owner email: {e}")
