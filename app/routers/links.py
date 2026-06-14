from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.booking import PublicLink, Booking
from app.models.schedule import Schedule
from app.routers.auth import get_current_user
from app.schemas.booking import PublicLinkCreate, PublicLinkOut, BookingOut
from app.services.tokens import generate_token

router = APIRouter(prefix="/api/links", tags=["Public Links"])


@router.post("", response_model=PublicLinkOut, status_code=201)
def create_link(
    data: PublicLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = db.query(Schedule).filter(
        Schedule.id == data.schedule_id, Schedule.user_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Agenda não encontrada")

    link = PublicLink(
        user_id=current_user.id,
        schedule_id=data.schedule_id,
        token=generate_token(32),
        label=data.label,
        expires_at=data.expires_at,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    result = PublicLinkOut.model_validate(link)
    result.booking_count = len(link.bookings)
    return result


@router.get("", response_model=List[PublicLinkOut])
def list_links(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    links = db.query(PublicLink).filter(PublicLink.user_id == current_user.id).all()
    result = []
    for link in links:
        out = PublicLinkOut.model_validate(link)
        out.booking_count = len([b for b in link.bookings if b.status == "confirmed"])
        result.append(out)
    return result


@router.put("/{link_id}/toggle", response_model=PublicLinkOut)
def toggle_link(
    link_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    link = db.query(PublicLink).filter(
        PublicLink.id == link_id, PublicLink.user_id == current_user.id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link não encontrado")
    link.is_active = not link.is_active
    db.commit()
    db.refresh(link)
    return link


@router.delete("/{link_id}", status_code=204)
def delete_link(
    link_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    link = db.query(PublicLink).filter(
        PublicLink.id == link_id, PublicLink.user_id == current_user.id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link não encontrado")
    db.delete(link)
    db.commit()


@router.get("/bookings", response_model=List[BookingOut])
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bookings = (
        db.query(Booking)
        .join(PublicLink)
        .filter(PublicLink.user_id == current_user.id, Booking.status == "confirmed")
        .order_by(Booking.start_datetime)
        .all()
    )
    return bookings


@router.delete("/bookings/{booking_id}", status_code=204)
def cancel_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = (
        db.query(Booking)
        .join(PublicLink)
        .filter(Booking.id == booking_id, PublicLink.user_id == current_user.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    booking.status = "cancelled"
    db.commit()
