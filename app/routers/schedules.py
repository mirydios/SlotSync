from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.schedule import Schedule, WeeklyAvailability
from app.routers.auth import get_current_user
from app.schemas.schedule import ScheduleCreate, ScheduleOut, ScheduleUpdate, WeeklyAvailabilityCreate

router = APIRouter(prefix="/api/schedules", tags=["Schedules"])


@router.post("", response_model=ScheduleOut, status_code=201)
def create_schedule(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = Schedule(
        user_id=current_user.id,
        name=data.name,
        slot_duration=data.slot_duration,
        buffer_time=data.buffer_time,
        advance_days=data.advance_days,
    )
    db.add(schedule)
    db.flush()

    for avail in (data.weekly_availability or []):
        wa = WeeklyAvailability(
            schedule_id=schedule.id,
            weekday=avail.weekday,
            start_time=avail.start_time,
            end_time=avail.end_time,
            is_active=avail.is_active,
        )
        db.add(wa)

    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("", response_model=List[ScheduleOut])
def list_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Schedule).filter(Schedule.user_id == current_user.id).all()


@router.get("/{schedule_id}", response_model=ScheduleOut)
def get_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id, Schedule.user_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Agenda não encontrada")
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(
    schedule_id: UUID,
    data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id, Schedule.user_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Agenda não encontrada")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id, Schedule.user_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Agenda não encontrada")
    db.delete(schedule)
    db.commit()


@router.post("/{schedule_id}/availability", response_model=ScheduleOut)
def set_weekly_availability(
    schedule_id: UUID,
    availability: List[WeeklyAvailabilityCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace all weekly availability for a schedule."""
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id, Schedule.user_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Agenda não encontrada")

    # Remove existing
    db.query(WeeklyAvailability).filter(WeeklyAvailability.schedule_id == schedule_id).delete()

    for avail in availability:
        wa = WeeklyAvailability(
            schedule_id=schedule_id,
            weekday=avail.weekday,
            start_time=avail.start_time,
            end_time=avail.end_time,
            is_active=avail.is_active,
        )
        db.add(wa)

    db.commit()
    db.refresh(schedule)
    return schedule
