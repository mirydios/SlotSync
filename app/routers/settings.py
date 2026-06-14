from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, datetime

from app.database import get_db
from app.models.user import User
from app.models.booking import Booking, PublicLink
from app.models.blocked_date import BlockedDate
from app.models.webhook import Webhook
from app.routers.auth import get_current_user
from pydantic import BaseModel, HttpUrl

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class UsernameUpdate(BaseModel):
    username: str

class BlockedDateCreate(BaseModel):
    date: date
    description: str | None = None

class BlockedDateOut(BaseModel):
    id: UUID
    date: date
    description: str | None

class WebhookCreate(BaseModel):
    url: HttpUrl
    is_active: bool = True

class WebhookOut(BaseModel):
    id: UUID
    url: HttpUrl
    is_active: bool

# --- USERNAME ---

@router.put("/username")
def update_username(
    data: UsernameUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conflict = db.query(User).filter(User.username == data.username, User.id != current_user.id).first()
    if conflict:
        raise HTTPException(status_code=400, detail="Este username já está em uso")
    current_user.username = data.username
    db.commit()
    return {"message": "Username atualizado com sucesso", "username": data.username}


# --- BLOCKED DATES ---

@router.get("/blocked-dates", response_model=List[BlockedDateOut])
def list_blocked_dates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(BlockedDate).filter(BlockedDate.user_id == current_user.id).all()

@router.post("/blocked-dates", response_model=BlockedDateOut)
def add_blocked_date(
    data: BlockedDateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    blocked = BlockedDate(
        user_id=current_user.id,
        date=data.date,
        description=data.description,
    )
    db.add(blocked)
    db.commit()
    db.refresh(blocked)
    return blocked

@router.delete("/blocked-dates/{blocked_id}", status_code=204)
def delete_blocked_date(
    blocked_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    blocked = db.query(BlockedDate).filter(BlockedDate.id == blocked_id, BlockedDate.user_id == current_user.id).first()
    if not blocked:
        raise HTTPException(status_code=404, detail="Data bloqueada não encontrada")
    db.delete(blocked)
    db.commit()


# --- WEBHOOKS ---

@router.get("/webhooks", response_model=List[WebhookOut])
def list_webhooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Webhook).filter(Webhook.user_id == current_user.id).all()

@router.post("/webhooks", response_model=WebhookOut)
def add_webhook(
    data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    webhook = Webhook(
        user_id=current_user.id,
        url=str(data.url),
        is_active=data.is_active,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook

@router.delete("/webhooks/{webhook_id}", status_code=204)
def delete_webhook(
    webhook_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.user_id == current_user.id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook não encontrado")
    db.delete(webhook)
    db.commit()


# --- STATS ---

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns booking counts for the last 7 days."""
    today = date.today()
    seven_days_ago = today - timedelta(days=6)
    
    # Query all bookings for this user's links
    bookings = (
        db.query(func.date(Booking.start_datetime).label("day"), func.count(Booking.id).label("count"))
        .join(PublicLink)
        .filter(
            PublicLink.user_id == current_user.id,
            Booking.status == "confirmed",
            func.date(Booking.start_datetime) >= seven_days_ago,
            func.date(Booking.start_datetime) <= today
        )
        .group_by(func.date(Booking.start_datetime))
        .all()
    )
    
    # Fill in missing days with 0
    stats_dict = {str(r.day): r.count for r in bookings}
    result = []
    
    for i in range(7):
        d = seven_days_ago + timedelta(days=i)
        d_str = d.isoformat()
        result.append({
            "date": d_str,
            "label": d.strftime("%d/%m"),
            "count": stats_dict.get(d_str, 0)
        })
        
    return {"last_7_days": result}

