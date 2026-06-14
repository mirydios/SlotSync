from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class PublicLinkCreate(BaseModel):
    schedule_id: UUID
    label: Optional[str] = "Link de Agendamento"
    expires_at: Optional[datetime] = None


class PublicLinkOut(BaseModel):
    id: UUID
    token: str
    label: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    booking_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class BookingCreate(BaseModel):
    guest_name: str
    guest_email: EmailStr
    guest_notes: Optional[str] = None
    start_datetime: datetime


class BookingReschedule(BaseModel):
    start_datetime: datetime


class BookingOut(BaseModel):
    id: UUID
    guest_name: str
    guest_email: EmailStr
    guest_notes: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    status: str
    cancellation_token: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SlotOut(BaseModel):
    start: datetime
    end: datetime
    available: bool


class PublicPageData(BaseModel):
    owner_name: str
    owner_bio: Optional[str] = None
    link_label: str
    slot_duration: int
    timezone: str
