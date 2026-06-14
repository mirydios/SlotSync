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


async def _send(subject: str, recipients: list, template_name: str, context: dict):
    """Internal helper to render and send an email."""
    conf = _get_mail_config()
    if not conf:
        logger.info(f"[EMAIL MOCK] To: {recipients} | Subject: {subject} | mail disabled")
        return

    template = jinja_env.get_template(template_name)
    body = template.render(**context, app_name=settings.EMAILS_FROM_NAME)

    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        logger.info(f"Email sent to {recipients}")
    except Exception as e:
        logger.error(f"Failed to send email to {recipients}: {e}")


# ─── BOOKING CONFIRMATION ──────────────────────────────────────────────────────

async def send_booking_confirmation_guest(
    guest_email: str,
    guest_name: str,
    owner_name: str,
    start_datetime: str,
    end_datetime: str,
    meeting_notes: Optional[str] = None,
    cancel_url: Optional[str] = None,
    reschedule_url: Optional[str] = None,
    ical_url: Optional[str] = None,
):
    await _send(
        subject=f"✅ Reunião confirmada com {owner_name}",
        recipients=[guest_email],
        template_name="booking_guest.html",
        context=dict(
            guest_name=guest_name,
            owner_name=owner_name,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            meeting_notes=meeting_notes,
            cancel_url=cancel_url,
            reschedule_url=reschedule_url,
            ical_url=ical_url,
        ),
    )


async def send_booking_notification_owner(
    owner_email: str,
    owner_name: str,
    guest_name: str,
    guest_email: str,
    guest_notes: Optional[str],
    start_datetime: str,
    end_datetime: str,
):
    await _send(
        subject=f"📅 Nova reunião agendada com {guest_name}",
        recipients=[owner_email],
        template_name="booking_owner.html",
        context=dict(
            owner_name=owner_name,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_notes=guest_notes,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        ),
    )


# ─── CANCELLATION ─────────────────────────────────────────────────────────────

async def send_cancellation_email_guest(
    guest_email: str,
    guest_name: str,
    owner_name: str,
    start_datetime: str,
):
    await _send(
        subject=f"❌ Reunião cancelada com {owner_name}",
        recipients=[guest_email],
        template_name="cancellation_guest.html",
        context=dict(
            guest_name=guest_name,
            owner_name=owner_name,
            start_datetime=start_datetime,
        ),
    )


async def send_cancellation_email_owner(
    owner_email: str,
    owner_name: str,
    guest_name: str,
    guest_email: str,
    start_datetime: str,
):
    await _send(
        subject=f"❌ Reunião cancelada por {guest_name}",
        recipients=[owner_email],
        template_name="cancellation_owner.html",
        context=dict(
            owner_name=owner_name,
            guest_name=guest_name,
            guest_email=guest_email,
            start_datetime=start_datetime,
        ),
    )
