import uuid
from datetime import UTC, datetime

from backend.app.db.session import Base
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


def utc_now():
    return datetime.now(UTC)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.00)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="service"
    )
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(
        "WaitlistEntry", back_populates="service"
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(50), nullable=False)

    service_id: Mapped[str] = mapped_column(String(36), ForeignKey("services.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(
        String(35), nullable=False, default="scheduled"
    )  # scheduled, completed, cancelled, no_show
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_recovery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    service: Mapped["Service"] = relationship("Service", back_populates="appointments")
    recovery_offers: Mapped[list["RecoveryOffer"]] = relationship(
        "RecoveryOffer", back_populates="appointment"
    )


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(50), nullable=False)

    service_id: Mapped[str] = mapped_column(String(36), ForeignKey("services.id"), nullable=False)
    preferred_start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    preferred_end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(35), nullable=False, default="active"
    )  # active, offered, fulfilled, cancelled
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    service: Mapped["Service"] = relationship("Service", back_populates="waitlist_entries")
    recovery_offers: Mapped[list["RecoveryOffer"]] = relationship(
        "RecoveryOffer", back_populates="waitlist_entry"
    )


class RecoveryOffer(Base):
    __tablename__ = "recovery_offers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("appointments.id"), nullable=False
    )
    waitlist_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("waitlist_entries.id"), nullable=False
    )

    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    status: Mapped[str] = mapped_column(
        String(35), nullable=False, default="pending"
    )  # pending, sent, accepted, expired, withdrawn

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    appointment: Mapped["Appointment"] = relationship(
        "Appointment", back_populates="recovery_offers"
    )
    waitlist_entry: Mapped["WaitlistEntry"] = relationship(
        "WaitlistEntry", back_populates="recovery_offers"
    )
    notification_logs: Mapped[list["NotificationLog"]] = relationship(
        "NotificationLog", back_populates="recovery_offer"
    )


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    offer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recovery_offers.id"), nullable=False
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="email")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="delivered"
    )  # delivered, failed
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    recovery_offer: Mapped["RecoveryOffer"] = relationship(
        "RecoveryOffer", back_populates="notification_logs"
    )


class BusinessSetting(Base):
    __tablename__ = "business_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    business_name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="SlotBack Wellness Spa"
    )
    default_offer_expiry_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    notification_email: Mapped[str] = mapped_column(
        String(255), nullable=False, default="staff@slotback.com"
    )
    auto_match_waitlist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    business_id: Mapped[str] = mapped_column(String(36), nullable=False, default="1")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="staff")  # "admin", "staff"
    business_id: Mapped[str] = mapped_column(String(36), nullable=False, default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
