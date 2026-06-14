from datetime import datetime, date as ddate
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.models.booking import PublicLink, Booking
from app.schemas.booking import BookingCreate, BookingOut
from app.services.availability import get_available_slots
from app.services.email import send_booking_confirmation_guest, send_booking_notification_owner
from app.services.tokens import generate_token

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
        "timezone": link.owner.timezone,
        "advance_days": link.schedule.advance_days,
    })


@router.get("/api/public/{token}/slots")
def get_slots(token: str, date: str, db: Session = Depends(get_db)):
    """Returns available slots for a given date (format: YYYY-MM-DD)."""
    link = _get_active_link(token, db)
    try:
        target_date = ddate.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")

    slots = get_available_slots(db, link, target_date)
    return {"date": date, "slots": slots, "timezone": link.owner.timezone}


@router.post("/api/public/{token}/book", response_model=BookingOut, status_code=201)
async def create_booking(token: str, data: BookingCreate, db: Session = Depends(get_db)):
    """Book a meeting slot via public link."""
    link = _get_active_link(token, db)
    schedule = link.schedule
    owner = link.owner

    # Validate that the requested slot is in the future
    if data.start_datetime <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Não é possível agendar no passado")

    # Calculate end time
    from datetime import timedelta
    end_dt = data.start_datetime + timedelta(minutes=schedule.slot_duration)

    # Check for conflicts
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

    # Format datetimes for email
    fmt = "%d/%m/%Y às %H:%M"
    start_str = data.start_datetime.strftime(fmt)
    end_str = end_dt.strftime(fmt)

    # Send confirmation emails (async, non-blocking)
    await send_booking_confirmation_guest(
        guest_email=data.guest_email,
        guest_name=data.guest_name,
        owner_name=owner.name,
        start_datetime=start_str,
        end_datetime=end_str,
        meeting_notes=data.guest_notes,
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

    # Update email flags
    booking.email_sent_guest = True
    booking.email_sent_owner = True
    db.commit()

    return booking
