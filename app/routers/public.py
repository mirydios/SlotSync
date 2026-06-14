from datetime import datetime, date as ddate, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from icalendar import Calendar, Event as CalEvent
import pytz
import uuid

from app.database import get_db
from app.models.booking import PublicLink, Booking
from app.schemas.booking import BookingCreate, BookingOut, BookingReschedule
from app.services.availability import get_available_slots
from app.services.email import (
    send_booking_confirmation_guest,
    send_booking_notification_owner,
    send_cancellation_email_guest,
    send_cancellation_email_owner,
)
from app.services.tokens import generate_token
from app.services.webhooks import trigger_webhook
from app.config import settings

router = APIRouter(tags=["Public"])

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _get_active_link(token: str, db: Session) -> PublicLink:
    link = db.query(PublicLink).filter(
        PublicLink.token == token,
        PublicLink.is_active == True,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link não encontrado ou inativo")
    if link.expires_at and link.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Este link expirou")
    return link


def _get_booking_by_cancel_token(cancel_token: str, db: Session) -> Booking:
    booking = db.query(Booking).filter(
        Booking.cancellation_token == cancel_token,
        Booking.status == "confirmed",
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado ou já cancelado")
    return booking


# ─── BOOKING PAGE ─────────────────────────────────────────────────────────────

@router.get("/book/{token}", response_class=HTMLResponse)
def booking_page(token: str, request: Request, db: Session = Depends(get_db)):
    link = _get_active_link(token, db)
    return templates.TemplateResponse("booking_page.html", {
        "request": request,
        "token": token,
        "owner_name": link.owner.name,
        "owner_bio": link.owner.bio or "",
        "link_label": link.label,
        "slot_duration": link.schedule.slot_duration,
        "durations_allowed": link.schedule.durations_allowed or [link.schedule.slot_duration],
        "timezone": link.owner.timezone,
        "advance_days": link.schedule.advance_days,
        "base_url": settings.APP_BASE_URL,
    })


# ─── CANCEL PAGE (convidado) ───────────────────────────────────────────────────

@router.get("/cancel/{cancel_token}", response_class=HTMLResponse)
def cancel_page(cancel_token: str, request: Request, db: Session = Depends(get_db)):
    booking = _get_booking_by_cancel_token(cancel_token, db)
    owner = booking.public_link.owner
    fmt = "%d/%m/%Y às %H:%M"
    return templates.TemplateResponse("cancel_page.html", {
        "request": request,
        "cancel_token": cancel_token,
        "guest_name": booking.guest_name,
        "owner_name": owner.name,
        "start_datetime": booking.start_datetime.strftime(fmt),
        "end_datetime": booking.end_datetime.strftime(fmt),
        "booking_id": str(booking.id),
        "link_token": booking.public_link.token,
    })


@router.post("/api/public/cancel/{cancel_token}")
async def confirm_cancel(cancel_token: str, db: Session = Depends(get_db)):
    """Guest cancels their own booking via token."""
    booking = _get_booking_by_cancel_token(cancel_token, db)
    owner = booking.public_link.owner
    fmt = "%d/%m/%Y às %H:%M"
    start_str = booking.start_datetime.strftime(fmt)

    booking.status = "cancelled"
    db.commit()

    await send_cancellation_email_guest(
        guest_email=booking.guest_email,
        guest_name=booking.guest_name,
        owner_name=owner.name,
        start_datetime=start_str,
    )
    await send_cancellation_email_owner(
        owner_email=owner.email,
        owner_name=owner.name,
        guest_name=booking.guest_name,
        guest_email=booking.guest_email,
        start_datetime=start_str,
    )

    await trigger_webhook(
        db=db,
        user_id=owner.id,
        event="booking.cancelled",
        payload={
            "booking_id": str(booking.id),
            "guest_name": booking.guest_name,
            "guest_email": booking.guest_email,
            "start_datetime": booking.start_datetime.isoformat(),
        }
    )

    return {"message": "Agendamento cancelado com sucesso"}


# ─── RESCHEDULE (convidado) ────────────────────────────────────────────────────

@router.get("/reschedule/{cancel_token}", response_class=HTMLResponse)
def reschedule_page(cancel_token: str, request: Request, db: Session = Depends(get_db)):
    """Show booking page in reschedule mode."""
    booking = _get_booking_by_cancel_token(cancel_token, db)
    link = booking.public_link
    return templates.TemplateResponse("booking_page.html", {
        "request": request,
        "token": link.token,
        "owner_name": link.owner.name,
        "owner_bio": link.owner.bio or "",
        "link_label": link.label,
        "slot_duration": link.schedule.slot_duration,
        "durations_allowed": link.schedule.durations_allowed or [link.schedule.slot_duration],
        "timezone": link.owner.timezone,
        "advance_days": link.schedule.advance_days,
        "base_url": settings.APP_BASE_URL,
        "reschedule_mode": True,
        "cancel_token": cancel_token,
        "old_start": booking.start_datetime.strftime("%d/%m/%Y às %H:%M"),
    })


@router.post("/api/public/reschedule/{cancel_token}", response_model=BookingOut, status_code=201)
async def reschedule_booking(
    cancel_token: str,
    data: BookingReschedule,
    db: Session = Depends(get_db),
):
    """Cancel existing booking and create a new one."""
    old_booking = _get_booking_by_cancel_token(cancel_token, db)
    link = old_booking.public_link
    schedule = link.schedule
    owner = link.owner

    if data.start_datetime <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Não é possível agendar no passado")

    duration = data.duration or schedule.slot_duration
    if schedule.durations_allowed and duration not in schedule.durations_allowed:
        raise HTTPException(status_code=400, detail="Duração não permitida para esta agenda")

    end_dt = data.start_datetime + timedelta(minutes=duration)

    # Check conflicts (excluding old booking itself)
    conflict = (
        db.query(Booking)
        .join(PublicLink)
        .filter(
            PublicLink.user_id == owner.id,
            Booking.status == "confirmed",
            Booking.id != old_booking.id,
            Booking.start_datetime < end_dt,
            Booking.end_datetime > data.start_datetime,
        )
        .first()
    )
    if conflict:
        raise HTTPException(status_code=409, detail="Este horário não está mais disponível")

    # Cancel old
    old_booking.status = "cancelled"
    db.flush()

    # Create new
    new_booking = Booking(
        public_link_id=link.id,
        guest_name=old_booking.guest_name,
        guest_email=old_booking.guest_email,
        guest_notes=old_booking.guest_notes,
        start_datetime=data.start_datetime,
        end_datetime=end_dt,
        status="confirmed",
        cancellation_token=generate_token(32),
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    fmt = "%d/%m/%Y às %H:%M"
    start_str = data.start_datetime.strftime(fmt)
    end_str = end_dt.strftime(fmt)
    cancel_url = f"{settings.APP_BASE_URL}/cancel/{new_booking.cancellation_token}"
    reschedule_url = f"{settings.APP_BASE_URL}/reschedule/{new_booking.cancellation_token}"

    await send_booking_confirmation_guest(
        guest_email=new_booking.guest_email,
        guest_name=new_booking.guest_name,
        owner_name=owner.name,
        start_datetime=start_str,
        end_datetime=end_str,
        meeting_notes=new_booking.guest_notes,
        cancel_url=cancel_url,
        reschedule_url=reschedule_url,
    )
    await send_booking_notification_owner(
        owner_email=owner.email,
        owner_name=owner.name,
        guest_name=new_booking.guest_name,
        guest_email=new_booking.guest_email,
        guest_notes=new_booking.guest_notes,
        start_datetime=start_str,
        end_datetime=end_str,
    )

    new_booking.email_sent_guest = True
    new_booking.email_sent_owner = True
    db.commit()

    await trigger_webhook(
        db=db,
        user_id=owner.id,
        event="booking.rescheduled",
        payload={
            "old_booking_id": str(old_booking.id),
            "new_booking_id": str(new_booking.id),
            "guest_name": new_booking.guest_name,
            "guest_email": new_booking.guest_email,
            "start_datetime": new_booking.start_datetime.isoformat(),
            "end_datetime": new_booking.end_datetime.isoformat(),
        }
    )

    return new_booking


# ─── ICAL DOWNLOAD ─────────────────────────────────────────────────────────────

@router.get("/api/public/booking/{cancel_token}/ical")
def download_ical(cancel_token: str, db: Session = Depends(get_db)):
    """Download .ics file for a confirmed booking."""
    booking = db.query(Booking).filter(
        Booking.cancellation_token == cancel_token,
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    owner = booking.public_link.owner
    tz = pytz.timezone(owner.timezone)

    cal = Calendar()
    cal.add("prodid", "-//SlotSync//SlotSync//PT")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "REQUEST")

    event = CalEvent()
    event.add("uid", str(uuid.uuid4()))
    event.add("summary", f"Reunião com {owner.name}")
    event.add("dtstart", tz.localize(booking.start_datetime))
    event.add("dtend", tz.localize(booking.end_datetime))
    event.add("organizer", owner.email)
    event.add("attendee", booking.guest_email)
    if booking.guest_notes:
        event.add("description", booking.guest_notes)

    cal.add_component(event)

    ics_content = cal.to_ical()
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="reuniao-{owner.name.replace(" ", "_")}.ics"'},
    )


# ─── SLOTS ─────────────────────────────────────────────────────────────────────

@router.get("/api/public/{token}/slots")
def get_slots(request: Request, token: str, date: str, db: Session = Depends(get_db)):
    """Returns available slots for a given date (format: YYYY-MM-DD). Rate limited to 30/min."""
    link = _get_active_link(token, db)
    try:
        target_date = ddate.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")

    duration = None
    if "duration" in request.query_params:
        try:
            duration = int(request.query_params["duration"])
            if link.schedule.durations_allowed and duration not in link.schedule.durations_allowed:
                raise HTTPException(status_code=400, detail="Duração não permitida")
        except ValueError:
            pass

    slots = get_available_slots(db, link, target_date, duration=duration)
    return {"date": date, "slots": slots, "timezone": link.owner.timezone}


# ─── BOOK ──────────────────────────────────────────────────────────────────────

@router.post("/api/public/{token}/book", response_model=BookingOut, status_code=201)
async def create_booking(request: Request, token: str, data: BookingCreate, db: Session = Depends(get_db)):
    """Book a meeting slot via public link. Rate limited to 5/min per IP."""
    link = _get_active_link(token, db)
    schedule = link.schedule
    owner = link.owner

    if data.start_datetime <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Não é possível agendar no passado")

    duration = data.duration or schedule.slot_duration
    if schedule.durations_allowed and duration not in schedule.durations_allowed:
        raise HTTPException(status_code=400, detail="Duração não permitida para esta agenda")

    end_dt = data.start_datetime + timedelta(minutes=duration)

    conflict = (
        db.query(Booking)
        .join(PublicLink)
        .filter(
            PublicLink.user_id == owner.id,
            Booking.status == "confirmed",
            Booking.start_datetime < end_dt,
            Booking.end_datetime > data.start_datetime,
        )
        .first()
    )
    if conflict:
        raise HTTPException(status_code=409, detail="Este horário não está mais disponível")

    booking = Booking(
        public_link_id=link.id,
        guest_name=data.guest_name,
        guest_email=data.guest_email,
        guest_notes=data.guest_notes,
        start_datetime=data.start_datetime,
        end_datetime=end_dt,
        status="confirmed",
        cancellation_token=generate_token(32),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    fmt = "%d/%m/%Y às %H:%M"
    start_str = data.start_datetime.strftime(fmt)
    end_str = end_dt.strftime(fmt)
    cancel_url = f"{settings.APP_BASE_URL}/cancel/{booking.cancellation_token}"
    reschedule_url = f"{settings.APP_BASE_URL}/reschedule/{booking.cancellation_token}"
    ical_url = f"{settings.APP_BASE_URL}/api/public/booking/{booking.cancellation_token}/ical"

    await send_booking_confirmation_guest(
        guest_email=data.guest_email,
        guest_name=data.guest_name,
        owner_name=owner.name,
        start_datetime=start_str,
        end_datetime=end_str,
        meeting_notes=data.guest_notes,
        cancel_url=cancel_url,
        reschedule_url=reschedule_url,
        ical_url=ical_url,
    )
    await send_booking_notification_owner(
        owner_email=owner.email,
        owner_name=owner.name,
        guest_name=data.guest_name,
        guest_email=data.guest_email,
        guest_notes=data.guest_notes,
        start_datetime=start_str,
        end_datetime=end_str,
    )

    booking.email_sent_guest = True
    booking.email_sent_owner = True
    db.commit()

    await trigger_webhook(
        db=db,
        user_id=owner.id,
        event="booking.created",
        payload={
            "booking_id": str(booking.id),
            "guest_name": booking.guest_name,
            "guest_email": booking.guest_email,
            "start_datetime": booking.start_datetime.isoformat(),
            "end_datetime": booking.end_datetime.isoformat(),
        }
    )

    return booking
