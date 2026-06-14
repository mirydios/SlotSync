import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class PublicLink(Base):
    """Tokenized public booking link per user."""
    __tablename__ = "public_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("schedules.id"), nullable=False)
    token = Column(String(64), unique=True, nullable=False, index=True)
    label = Column(String(100), default="Link de Agendamento")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="public_links")
    schedule = relationship("Schedule")
    bookings = relationship("Booking", back_populates="public_link", cascade="all, delete-orphan")


class Booking(Base):
    """A confirmed meeting booking."""
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_link_id = Column(UUID(as_uuid=True), ForeignKey("public_links.id"), nullable=False)
    guest_name = Column(String(100), nullable=False)
    guest_email = Column(String(255), nullable=False)
    guest_notes = Column(Text, nullable=True)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    status = Column(String(20), default="confirmed")  # confirmed, cancelled
    cancellation_token = Column(String(64), unique=True, nullable=True)
    email_sent_guest = Column(Boolean, default=False)
    email_sent_owner = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    public_link = relationship("PublicLink", back_populates="bookings")
