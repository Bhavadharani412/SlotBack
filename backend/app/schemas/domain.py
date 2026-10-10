from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ServiceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    duration_minutes: int = Field(..., gt=0)
    price: float = Field(..., ge=0.0)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    price: float | None = None
    is_active: bool | None = None


class ServiceOut(ServiceBase):
    id: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AppointmentBase(BaseModel):
    customer_name: str = Field(..., min_length=1)
    customer_email: EmailStr
    customer_phone: str = Field(..., min_length=1)
    service_id: str
    start_time: datetime


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentCancel(BaseModel):
    reason: str | None = None


class AppointmentOut(AppointmentBase):
    id: str
    end_time: datetime
    status: str
    cancellation_reason: str | None = None
    cancelled_at: datetime | None = None
    is_recovery: bool
    created_at: datetime
    service: ServiceOut | None = None
    model_config = ConfigDict(from_attributes=True)


class WaitlistBase(BaseModel):
    customer_name: str = Field(..., min_length=1)
    customer_email: EmailStr
    customer_phone: str = Field(..., min_length=1)
    service_id: str
    preferred_start_date: datetime
    preferred_end_date: datetime
    notes: str | None = None


class WaitlistCreate(WaitlistBase):
    pass


class WaitlistUpdate(BaseModel):
    preferred_start_date: datetime | None = None
    preferred_end_date: datetime | None = None
    notes: str | None = None
    status: str | None = None


class WaitlistOut(WaitlistBase):
    id: str
    status: str
    created_at: datetime
    service: ServiceOut | None = None
    model_config = ConfigDict(from_attributes=True)


class NotificationLogOut(BaseModel):
    id: str
    offer_id: str
    recipient_email: str
    channel: str
    status: str
    retry_count: int
    error_message: str | None = None
    sent_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RecoveryOfferOut(BaseModel):
    id: str
    appointment_id: str
    waitlist_id: str
    token: str
    status: str
    expires_at: datetime
    sent_at: datetime | None = None
    accepted_at: datetime | None = None
    created_at: datetime
    appointment: AppointmentOut | None = None
    waitlist_entry: WaitlistOut | None = None
    notification_logs: list[NotificationLogOut] = []
    model_config = ConfigDict(from_attributes=True)


class RecoveryOfferCreate(BaseModel):
    appointment_id: str
    waitlist_id: str
    expiry_minutes: int | None = 60
    simulate_notification_failure: bool | None = False


class OfferAcceptResponse(BaseModel):
    message: str
    status: str
    appointment: AppointmentOut
    offer: RecoveryOfferOut


class BusinessSettingBase(BaseModel):
    business_name: str
    default_offer_expiry_minutes: int = Field(..., gt=0)
    notification_email: EmailStr
    auto_match_waitlist: bool


class BusinessSettingOut(BusinessSettingBase):
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MetricsOut(BaseModel):
    eligible_cancellations: int
    recovered_appointments: int
    recovery_rate: float
    time_to_refill_median_minutes: float | None = None
    notification_failure_rate: float
    total_active_waitlist: int
    active_offers_count: int
    period: str = "all_time"


class MatchRecommendationOut(BaseModel):
    cancelled_appointment: AppointmentOut
    eligible_waitlist_entries: list[WaitlistOut]
