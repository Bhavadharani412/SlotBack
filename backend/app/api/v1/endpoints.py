from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.domain import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentOut,
    BusinessSettingBase,
    BusinessSettingOut,
    MatchRecommendationOut,
    MetricsOut,
    NotificationLogOut,
    OfferAcceptResponse,
    RecoveryOfferCreate,
    RecoveryOfferOut,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
    WaitlistCreate,
    WaitlistOut,
)
from backend.app.services.recovery_service import SlotBackService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> SlotBackService:
    return SlotBackService(db)


# ------------------ Services ------------------
@router.get("/services", response_model=List[ServiceOut], tags=["services"])
def list_services(
    active_only: bool = Query(False),
    service: SlotBackService = Depends(get_service),
):
    return service.get_services(active_only=active_only)


@router.post("/services", response_model=ServiceOut, status_code=status.HTTP_201_CREATED, tags=["services"])
def create_service(
    payload: ServiceCreate,
    service: SlotBackService = Depends(get_service),
):
    return service.create_service(payload)


@router.put("/services/{service_id}", response_model=ServiceOut, tags=["services"])
def update_service(
    service_id: str,
    payload: ServiceUpdate,
    service: SlotBackService = Depends(get_service),
):
    return service.update_service(service_id, payload)


# ------------------ Appointments ------------------
@router.get("/appointments", response_model=List[AppointmentOut], tags=["appointments"])
def list_appointments(
    date: Optional[str] = Query(None),
    service_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    service: SlotBackService = Depends(get_service),
):
    return service.get_appointments(date_str=date, service_id=service_id, status_filter=status_filter)


@router.post("/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED, tags=["appointments"])
def create_appointment(
    payload: AppointmentCreate,
    service: SlotBackService = Depends(get_service),
):
    return service.create_appointment(payload)


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentOut, tags=["appointments"])
def cancel_appointment(
    appointment_id: str,
    payload: AppointmentCancel,
    service: SlotBackService = Depends(get_service),
):
    return service.cancel_appointment(appointment_id, reason=payload.reason)


# ------------------ Waitlist ------------------
@router.get("/waitlist", response_model=List[WaitlistOut], tags=["waitlist"])
def list_waitlist(
    status_filter: Optional[str] = Query(None, alias="status"),
    service: SlotBackService = Depends(get_service),
):
    return service.get_waitlist(status_filter=status_filter)


@router.post("/waitlist", response_model=WaitlistOut, status_code=status.HTTP_201_CREATED, tags=["waitlist"])
def create_waitlist_entry(
    payload: WaitlistCreate,
    service: SlotBackService = Depends(get_service),
):
    return service.create_waitlist_entry(payload)


@router.delete("/waitlist/{entry_id}", response_model=WaitlistOut, tags=["waitlist"])
def cancel_waitlist_entry(
    entry_id: str,
    service: SlotBackService = Depends(get_service),
):
    return service.cancel_waitlist_entry(entry_id)


# ------------------ Slot Recovery & Offers ------------------
@router.get("/recovery/offers", response_model=List[RecoveryOfferOut], tags=["recovery"])
def list_recovery_offers(service: SlotBackService = Depends(get_service)):
    return service.get_offers()


@router.post("/recovery/offers", response_model=RecoveryOfferOut, status_code=status.HTTP_201_CREATED, tags=["recovery"])
def create_recovery_offer(
    payload: RecoveryOfferCreate,
    service: SlotBackService = Depends(get_service),
):
    return service.create_recovery_offer(payload)


@router.get("/recovery/offers/{token_or_id}", response_model=RecoveryOfferOut, tags=["recovery"])
def get_recovery_offer(
    token_or_id: str,
    service: SlotBackService = Depends(get_service),
):
    return service.get_offer_by_token(token_or_id)


@router.post("/recovery/offers/{token_or_id}/accept", response_model=OfferAcceptResponse, tags=["recovery"])
def accept_recovery_offer(
    token_or_id: str,
    service: SlotBackService = Depends(get_service),
):
    return service.accept_offer(token_or_id)


@router.post("/recovery/offers/{offer_id}/withdraw", response_model=RecoveryOfferOut, tags=["recovery"])
def withdraw_recovery_offer(
    offer_id: str,
    service: SlotBackService = Depends(get_service),
):
    return service.withdraw_offer(offer_id)


@router.post("/recovery/notifications/{notification_id}/retry", response_model=NotificationLogOut, tags=["recovery"])
def retry_notification(
    notification_id: str,
    service: SlotBackService = Depends(get_service),
):
    return service.retry_notification(notification_id)


# ------------------ Reports & Metrics ------------------
@router.get("/reports/metrics", response_model=MetricsOut, tags=["reports"])
def get_metrics(service: SlotBackService = Depends(get_service)):
    return service.get_metrics()


# ------------------ Settings ------------------
@router.get("/settings", response_model=BusinessSettingOut, tags=["settings"])
def get_settings(service: SlotBackService = Depends(get_service)):
    return service.get_or_create_settings()


@router.put("/settings", response_model=BusinessSettingOut, tags=["settings"])
def update_settings(
    payload: BusinessSettingBase,
    service: SlotBackService = Depends(get_service),
):
    return service.update_settings(payload)
