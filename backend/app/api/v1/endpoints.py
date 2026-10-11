from typing import Annotated

from backend.app.core.auth import (
    get_current_user,
    require_admin,
    require_staff,
    security_bearer,
)
from backend.app.core.rate_limit import rate_limit
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.db.session import get_db
from backend.app.models.domain import User
from backend.app.schemas.domain import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentOut,
    BusinessSettingBase,
    BusinessSettingOut,
    MetricsOut,
    NotificationLogOut,
    OfferAcceptResponse,
    RecoveryOfferCreate,
    RecoveryOfferOut,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
    TokenOut,
    UserCreate,
    UserLogin,
    UserOut,
    WaitlistCreate,
    WaitlistOut,
)
from backend.app.services.recovery_service import SlotBackService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> SlotBackService:
    return SlotBackService(db)


# ------------------ Authentication & Staff Accounts ------------------
@router.post(
    "/auth/login",
    response_model=TokenOut,
    tags=["auth"],
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated.",
        )

    access_token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "business_id": user.business_id,
        }
    )
    return TokenOut(access_token=access_token, token_type="bearer", user=user)


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
def get_current_user_profile(
    current_user: Annotated[User, Depends(require_staff)],
):
    return current_user


@router.post(
    "/auth/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
def create_staff_user(
    payload: UserCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )
    new_user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        business_id=current_user.business_id,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get(
    "/auth/users",
    response_model=list[UserOut],
    tags=["auth"],
)
def list_staff_users(
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    stmt = (
        select(User)
        .where(User.business_id == current_user.business_id)
        .order_by(User.created_at.desc())
    )
    return list(db.scalars(stmt).all())


# ------------------ Services ------------------
@router.get("/services", response_model=list[ServiceOut], tags=["services"])
def list_services(
    active_only: bool = Query(False),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)] = None,
    db: Session = Depends(get_db),
):
    # Public customer booking requires active services; full list requires staff credentials
    if not active_only:
        get_current_user(credentials=credentials, db=db)
    service = SlotBackService(db)
    return service.get_services(active_only=active_only)


@router.post(
    "/services",
    response_model=ServiceOut,
    status_code=status.HTTP_201_CREATED,
    tags=["services"],
)
def create_service(
    payload: ServiceCreate,
    current_user: Annotated[User, Depends(require_admin)],
    service: SlotBackService = Depends(get_service),
):
    return service.create_service(payload)


@router.put("/services/{service_id}", response_model=ServiceOut, tags=["services"])
def update_service(
    service_id: str,
    payload: ServiceUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    service: SlotBackService = Depends(get_service),
):
    return service.update_service(service_id, payload)


# ------------------ Appointments ------------------
@router.get("/appointments", response_model=list[AppointmentOut], tags=["appointments"])
def list_appointments(
    current_user: Annotated[User, Depends(require_staff)],
    date: str | None = Query(None),
    service_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    service: SlotBackService = Depends(get_service),
):
    return service.get_appointments(
        date_str=date, service_id=service_id, status_filter=status_filter
    )


@router.post(
    "/appointments",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
    tags=["appointments"],
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def create_appointment(
    payload: AppointmentCreate,
    service: SlotBackService = Depends(get_service),
):
    # Public customer booking flow, throttled against abuse
    return service.create_appointment(payload)


@router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentOut,
    tags=["appointments"],
)
def cancel_appointment(
    appointment_id: str,
    payload: AppointmentCancel,
    current_user: Annotated[User, Depends(require_staff)],
    service: SlotBackService = Depends(get_service),
):
    return service.cancel_appointment(appointment_id, reason=payload.reason)


# ------------------ Waitlist ------------------
@router.get("/waitlist", response_model=list[WaitlistOut], tags=["waitlist"])
def list_waitlist(
    current_user: Annotated[User, Depends(require_staff)],
    status_filter: str | None = Query(None, alias="status"),
    service: SlotBackService = Depends(get_service),
):
    return service.get_waitlist(status_filter=status_filter)


@router.post(
    "/waitlist",
    response_model=WaitlistOut,
    status_code=status.HTTP_201_CREATED,
    tags=["waitlist"],
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def create_waitlist_entry(
    payload: WaitlistCreate,
    service: SlotBackService = Depends(get_service),
):
    # Public customer waitlist flow, throttled against abuse
    return service.create_waitlist_entry(payload)


@router.delete("/waitlist/{entry_id}", response_model=WaitlistOut, tags=["waitlist"])
def cancel_waitlist_entry(
    entry_id: str,
    current_user: Annotated[User, Depends(require_staff)],
    service: SlotBackService = Depends(get_service),
):
    return service.cancel_waitlist_entry(entry_id)


# ------------------ Slot Recovery & Offers ------------------
@router.get("/recovery/offers", response_model=list[RecoveryOfferOut], tags=["recovery"])
def list_recovery_offers(
    current_user: Annotated[User, Depends(require_staff)],
    service: SlotBackService = Depends(get_service),
):
    return service.get_offers()


@router.post(
    "/recovery/offers",
    response_model=RecoveryOfferOut,
    status_code=status.HTTP_201_CREATED,
    tags=["recovery"],
)
def create_recovery_offer(
    payload: RecoveryOfferCreate,
    current_user: Annotated[User, Depends(require_staff)],
    service: SlotBackService = Depends(get_service),
):
    return service.create_recovery_offer(payload)


@router.get(
    "/recovery/offers/{token_or_id}",
    response_model=RecoveryOfferOut,
    tags=["recovery"],
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def get_recovery_offer(
    token_or_id: str,
    service: SlotBackService = Depends(get_service),
):
    # Customer capability token endpoint
    return service.get_offer_by_token(token_or_id)


@router.post(
    "/recovery/offers/{token_or_id}/accept",
    response_model=OfferAcceptResponse,
    tags=["recovery"],
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def accept_recovery_offer(
    token_or_id: str,
    service: SlotBackService = Depends(get_service),
):
    # Customer capability token acceptance endpoint
    return service.accept_offer(token_or_id)


@router.post(
    "/recovery/offers/{offer_id}/withdraw",
    response_model=RecoveryOfferOut,
    tags=["recovery"],
)
def withdraw_recovery_offer(
    offer_id: str,
    current_user: Annotated[User, Depends(require_staff)],
    service: SlotBackService = Depends(get_service),
):
    return service.withdraw_offer(offer_id)


@router.post(
    "/recovery/notifications/{notification_id}/retry",
    response_model=NotificationLogOut,
    tags=["recovery"],
)
def retry_notification(
    notification_id: str,
    current_user: Annotated[User, Depends(require_staff)],
    service: SlotBackService = Depends(get_service),
):
    return service.retry_notification(notification_id)


# ------------------ Reports & Metrics ------------------
@router.get("/reports/metrics", response_model=MetricsOut, tags=["reports"])
def get_metrics(
    current_user: Annotated[User, Depends(require_staff)],
    service: SlotBackService = Depends(get_service),
):
    return service.get_metrics()


# ------------------ Settings ------------------
@router.get("/settings", response_model=BusinessSettingOut, tags=["settings"])
def get_settings(
    current_user: Annotated[User, Depends(require_staff)],
    service: SlotBackService = Depends(get_service),
):
    return service.get_or_create_settings()


@router.put("/settings", response_model=BusinessSettingOut, tags=["settings"])
def update_settings(
    payload: BusinessSettingBase,
    current_user: Annotated[User, Depends(require_admin)],
    service: SlotBackService = Depends(get_service),
):
    return service.update_settings(payload)
