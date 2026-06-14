from datetime import datetime, timedelta, time as dtime
from typing import List
from sqlalchemy.orm import Session
from app.models.schedule import Schedule, WeeklyAvailability
from app.models.booking import Booking, PublicLink
import pytz


def get_available_slots(
    db: Session,
    public_link: PublicLink,
    target_date: datetime.date,
) -> List[dict]:
    """
    Returns list of available time slots for a given date.
    Respects: weekly availability, slot duration, buffer, existing bookings.
    """
    schedule: Schedule = public_link.schedule
    owner = public_link.owner
    tz = pytz.timezone(owner.timezone)

    # Weekday: 0=Mon, 6=Sun
    weekday = target_date.weekday()

    # Get availability windows for this weekday
    windows: List[WeeklyAvailability] = (
        db.query(WeeklyAvailability)
        .filter(
            WeeklyAvailability.schedule_id == schedule.id,
            WeeklyAvailability.weekday == weekday,
            WeeklyAvailability.is_active == True,
        )
        .all()
    )

    if not windows:
        return []

    slot_duration = timedelta(minutes=schedule.slot_duration)
    buffer = timedelta(minutes=schedule.buffer_time)

    # Fetch existing confirmed bookings for that date
    day_start = tz.localize(datetime.combine(target_date, dtime.min)).astimezone(pytz.utc).replace(tzinfo=None)
    day_end = tz.localize(datetime.combine(target_date, dtime.max)).astimezone(pytz.utc).replace(tzinfo=None)

    booked = (
        db.query(Booking)
        .join(PublicLink)
        .filter(
            PublicLink.user_id == public_link.user_id,
            Booking.status == "confirmed",
            Booking.start_datetime >= day_start,
            Booking.start_datetime <= day_end,
        )
        .all()
    )

    booked_ranges = [(b.start_datetime, b.end_datetime) for b in booked]

    slots = []
    now_utc = datetime.utcnow()

    for window in windows:
        current = datetime.combine(target_date, window.start_time)
        current_local = tz.localize(current)
        window_end = datetime.combine(target_date, window.end_time)
        window_end_local = tz.localize(window_end)

        while current_local + slot_duration <= window_end_local:
            slot_start_utc = current_local.astimezone(pytz.utc).replace(tzinfo=None)
            slot_end_utc = (current_local + slot_duration).astimezone(pytz.utc).replace(tzinfo=None)

            # Don't show past slots
            if slot_start_utc <= now_utc:
                current_local += slot_duration + buffer
                continue

            # Check overlap with existing bookings
            is_free = True
            for b_start, b_end in booked_ranges:
                if not (slot_end_utc <= b_start or slot_start_utc >= b_end):
                    is_free = False
                    break

            if is_free:
                slots.append({
                    "start": current_local.isoformat(),
                    "end": (current_local + slot_duration).isoformat(),
                    "start_utc": slot_start_utc.isoformat(),
                    "end_utc": slot_end_utc.isoformat(),
                })

            current_local += slot_duration + buffer

    return slots
