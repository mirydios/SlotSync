import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Schedule(Base):
    """Main schedule configuration per user."""
    __tablename__ = "schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), default="Minha Agenda")
    slot_duration = Column(Integer, default=30)       # minutes
    buffer_time = Column(Integer, default=0)           # minutes between meetings
    advance_days = Column(Integer, default=30)         # how many days ahead can be booked
    is_active = Column(Boolean, default=True)

    # Relationships
    owner = relationship("User", back_populates="schedules")
    weekly_availability = relationship(
        "WeeklyAvailability", back_populates="schedule", cascade="all, delete-orphan"
    )


class WeeklyAvailability(Base):
    """Defines available time windows per weekday."""
    __tablename__ = "weekly_availability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("schedules.id"), nullable=False)
    # 0=Monday, 1=Tuesday, ..., 6=Sunday
    weekday = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True)

    schedule = relationship("Schedule", back_populates="weekly_availability")
