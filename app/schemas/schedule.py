from pydantic import BaseModel
from typing import Optional, List
from datetime import time
from uuid import UUID


class WeeklyAvailabilityCreate(BaseModel):
    weekday: int  # 0=Mon ... 6=Sun
    start_time: time
    end_time: time
    is_active: bool = True


class WeeklyAvailabilityOut(WeeklyAvailabilityCreate):
    id: UUID
    model_config = {"from_attributes": True}


class ScheduleCreate(BaseModel):
    name: Optional[str] = "Minha Agenda"
    slot_duration: Optional[int] = 30
    buffer_time: Optional[int] = 0
    advance_days: Optional[int] = 30
    weekly_availability: Optional[List[WeeklyAvailabilityCreate]] = []


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    slot_duration: Optional[int] = None
    buffer_time: Optional[int] = None
    advance_days: Optional[int] = None
    is_active: Optional[bool] = None


class ScheduleOut(BaseModel):
    id: UUID
    name: str
    slot_duration: int
    buffer_time: int
    advance_days: int
    is_active: bool
    weekly_availability: List[WeeklyAvailabilityOut] = []

    model_config = {"from_attributes": True}
