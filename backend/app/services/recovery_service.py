import statistics
import uuid
from datetime import UTC, datetime, timedelta

from backend.app.models.domain import (
    Appointment,
    BusinessSetting,
    NotificationLog,
    RecoveryOffer,
    Service,
    WaitlistEntry,
)
from backend.app.schemas.domain import (
    AppointmentCreate,
    BusinessSettingBase,
    MetricsOut,
    RecoveryOfferCreate,
    ServiceCreate,
    ServiceUpdate,
    WaitlistCreate,
)
from backend.app.services.notification_provider import notification_provider
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload


def utc_now() -> datetime:
    return datetime.now(UTC)


class SlotBackService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------ Services ------------------
    def get_services(self, active_only: bool = False) -> list[Service]:
        stmt = select(Service)
        if active_only:
            stmt = stmt.where(Service.is_active.is_(True))
        return list(self.db.scalars(stmt.order_by(Service.name)).all())

    def create_service(self, data: ServiceCreate) -> Service:
        service = Service(
            name=data.name,
            description=data.description,
            duration_minutes=data.duration_minutes,
            price=data.price,
            is_active=True,
        )
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        return service

    def update_service(self, service_id: str, data: ServiceUpdate) -> Service:
        service = self.db.get(Service, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        if data.name is not None:
            service.name = data.name
        if data.description is not None:
            service.description = data.description
        if data.duration_minutes is not None:
            service.duration_minutes = data.duration_minutes
        if data.price is not None:
            service.price = data.price
        if data.is_active is not None:
            service.is_active = data.is_active
        self.db.commit()
        self.db.refresh(service)
        return service

    # ------------------ Appointments ------------------
    def get_appointments(
        self,
        date_str: str | None = None,
        service_id: str | None = None,
        status_filter: str | None = None,
    ) -> list[Appointment]:
        stmt = select(Appointment).options(joinedload(Appointment.service))
        if service_id:
            stmt = stmt.where(Appointment.service_id == service_id)
        if status_filter:
            stmt = stmt.where(Appointment.status == status_filter)
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                stmt = stmt.where(func.date(Appointment.start_time) == target_date)
            except ValueError:
                pass
        return list(self.db.scalars(stmt.order_by(Appointment.start_time.desc())).all())

    def create_appointment(self, data: AppointmentCreate, is_recovery: bool = False) -> Appointment:
        service = self.db.get(Service, data.service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        end_time = data.start_time + timedelta(minutes=service.duration_minutes)

        # Check conflict
        conflict_stmt = select(Appointment).where(
            Appointment.service_id == data.service_id,
            Appointment.status == "scheduled",
            Appointment.start_time < end_time,
            Appointment.end_time > data.start_time,
        )
        if self.db.scalar(conflict_stmt):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Time slot is already booked for this service.",
            )

        appointment = Appointment(
            customer_name=data.customer_name,
            customer_email=data.customer_email,
            customer_phone=data.customer_phone,
            service_id=data.service_id,
            start_time=data.start_time,
            end_time=end_time,
            status="scheduled",
            is_recovery=is_recovery,
        )
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def cancel_appointment(self, appointment_id: str, reason: str | None = None) -> Appointment:
        appointment = self.db.get(Appointment, appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        if appointment.status == "cancelled":
            return appointment

        appointment.status = "cancelled"
        appointment.cancellation_reason = reason
        appointment.cancelled_at = utc_now()

        self.db.commit()
        self.db.refresh(appointment)

        # Trigger auto-recovery check
        setting = self.get_or_create_settings()
        if setting.auto_match_waitlist:
            self.auto_issue_recovery_offer(appointment)

        return appointment

    # ------------------ Waitlist ------------------
    def get_waitlist(self, status_filter: str | None = None) -> list[WaitlistEntry]:
        stmt = select(WaitlistEntry).options(joinedload(WaitlistEntry.service))
        if status_filter:
            stmt = stmt.where(WaitlistEntry.status == status_filter)
        return list(self.db.scalars(stmt.order_by(WaitlistEntry.created_at.desc())).all())

    def create_waitlist_entry(self, data: WaitlistCreate) -> WaitlistEntry:
        service = self.db.get(Service, data.service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        entry = WaitlistEntry(
            customer_name=data.customer_name,
            customer_email=data.customer_email,
            customer_phone=data.customer_phone,
            service_id=data.service_id,
            preferred_start_date=data.preferred_start_date,
            preferred_end_date=data.preferred_end_date,
            notes=data.notes,
            status="active",
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def cancel_waitlist_entry(self, entry_id: str) -> WaitlistEntry:
        entry = self.db.get(WaitlistEntry, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Waitlist entry not found")
        entry.status = "cancelled"
        self.db.commit()
        self.db.refresh(entry)
        return entry

    # ------------------ Recovery & Offers ------------------
    def get_offers(self) -> list[RecoveryOffer]:
        stmt = (
            select(RecoveryOffer)
            .options(
                joinedload(RecoveryOffer.appointment).joinedload(Appointment.service),
                joinedload(RecoveryOffer.waitlist_entry),
                joinedload(RecoveryOffer.notification_logs),
            )
            .order_by(RecoveryOffer.created_at.desc())
        )
        offers = list(self.db.scalars(stmt).unique().all())
        now = utc_now()
        # Lazily mark expired
        for offer in offers:
            if offer.status in ["pending", "sent"] and offer.expires_at < now:
                offer.status = "expired"
                self.db.add(offer)
        self.db.commit()
        return offers

    def get_offer_by_token(self, token_or_id: str) -> RecoveryOffer:
        stmt = (
            select(RecoveryOffer)
            .where((RecoveryOffer.token == token_or_id) | (RecoveryOffer.id == token_or_id))
            .options(
                joinedload(RecoveryOffer.appointment).joinedload(Appointment.service),
                joinedload(RecoveryOffer.waitlist_entry),
                joinedload(RecoveryOffer.notification_logs),
            )
        )
        offer = self.db.scalars(stmt).unique().first()
        if not offer:
            raise HTTPException(status_code=404, detail="Recovery offer not found")

        # Check expiry
        now = utc_now()
        if offer.status in ["pending", "sent"] and offer.expires_at < now:
            offer.status = "expired"
            self.db.commit()
            self.db.refresh(offer)
        return offer

    def auto_issue_recovery_offer(self, appointment: Appointment) -> RecoveryOffer | None:
        # Find eligible waitlisted customers
        matches = self.get_eligible_waitlist_for_appointment(appointment)
        if not matches:
            return None

        target_waitlist = matches[0]
        setting = self.get_or_create_settings()
        return self.create_recovery_offer(
            RecoveryOfferCreate(
                appointment_id=appointment.id,
                waitlist_id=target_waitlist.id,
                expiry_minutes=setting.default_offer_expiry_minutes,
            )
        )

    def get_eligible_waitlist_for_appointment(
        self, appointment: Appointment
    ) -> list[WaitlistEntry]:
        stmt = (
            select(WaitlistEntry)
            .where(
                WaitlistEntry.service_id == appointment.service_id,
                WaitlistEntry.status == "active",
                WaitlistEntry.preferred_start_date <= appointment.start_time,
                WaitlistEntry.preferred_end_date >= appointment.start_time,
            )
            .order_by(WaitlistEntry.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def create_recovery_offer(self, data: RecoveryOfferCreate) -> RecoveryOffer:
        appointment = self.db.get(Appointment, data.appointment_id)
        waitlist = self.db.get(WaitlistEntry, data.waitlist_id)
        if not appointment or appointment.status != "cancelled":
            raise HTTPException(
                status_code=400, detail="Appointment must be cancelled to offer recovery."
            )
        if not waitlist or waitlist.status not in ["active", "offered"]:
            raise HTTPException(status_code=400, detail="Waitlist entry is not eligible.")

        # Invariant: Customer must match the appointment service
        if waitlist.service_id != appointment.service_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Waitlist customer is not eligible: service mismatch.",
            )

        # Invariant: Appointment time must fall within customer's preferred date window
        appt_start = (
            appointment.start_time
            if appointment.start_time.tzinfo
            else appointment.start_time.replace(tzinfo=UTC)
        )
        pref_start = (
            waitlist.preferred_start_date
            if waitlist.preferred_start_date.tzinfo
            else waitlist.preferred_start_date.replace(tzinfo=UTC)
        )
        pref_end = (
            waitlist.preferred_end_date
            if waitlist.preferred_end_date.tzinfo
            else waitlist.preferred_end_date.replace(tzinfo=UTC)
        )

        if appt_start < pref_start or appt_start > pref_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Waitlist customer is not eligible: appointment time is outside preferred window.",
            )

        # Check existing active offer for this slot
        existing_offer = self.db.scalar(
            select(RecoveryOffer).where(
                RecoveryOffer.appointment_id == appointment.id,
                RecoveryOffer.status.in_(["pending", "sent", "accepted"]),
            )
        )
        if existing_offer:
            if existing_offer.status == "accepted":
                raise HTTPException(
                    status_code=400, detail="Slot is already recovered and confirmed."
                )
            # If expired, mark as expired
            if existing_offer.expires_at < utc_now():
                existing_offer.status = "expired"
            else:
                raise HTTPException(
                    status_code=400, detail="An active offer already exists for this slot."
                )

        expiry_mins = data.expiry_minutes or 60
        expires_at = utc_now() + timedelta(minutes=expiry_mins)
        token = str(uuid.uuid4())

        offer = RecoveryOffer(
            appointment_id=appointment.id,
            waitlist_id=waitlist.id,
            token=token,
            status="sent",
            expires_at=expires_at,
            sent_at=utc_now(),
        )
        self.db.add(offer)

        # Update waitlist status
        waitlist.status = "offered"

        # Dispatch notification via provider boundary
        if data.simulate_notification_failure:
            notif_status = "failed"
            error_msg = "SMTP delivery failure: Connection timed out"
        else:
            try:
                service_name = appointment.service.name if appointment.service else "Service"
                delivery_result = notification_provider.send_recovery_offer_email(
                    recipient_email=waitlist.customer_email,
                    customer_name=waitlist.customer_name,
                    service_name=service_name,
                    offer_url=f"/offer/{token}",
                    expiry_minutes=expiry_mins,
                )
                notif_status = delivery_result.status
                error_msg = delivery_result.error_message
            except Exception as exc:
                notif_status = "failed"
                error_msg = f"Delivery error: {str(exc)}"

        notif_log = NotificationLog(
            recovery_offer=offer,
            recipient_email=waitlist.customer_email,
            channel="email",
            status=notif_status,
            retry_count=0,
            error_message=error_msg,
            sent_at=utc_now(),
        )
        self.db.add(notif_log)

        self.db.commit()
        self.db.refresh(offer)
        return offer

    def accept_offer(self, token_or_id: str) -> dict:
        # ATOMIC ACCEPTANCE WORKFLOW with DB locking / transaction
        offer = self.db.scalar(
            select(RecoveryOffer)
            .where((RecoveryOffer.token == token_or_id) | (RecoveryOffer.id == token_or_id))
            .with_for_update()
        )
        if not offer:
            raise HTTPException(status_code=404, detail="Recovery offer not found.")

        if offer.status == "accepted":
            raise HTTPException(
                status_code=400, detail="This offer has already been accepted and confirmed."
            )

        if offer.status in ["expired", "withdrawn"]:
            raise HTTPException(
                status_code=400, detail=f"Offer is no longer valid (Status: {offer.status})."
            )

        if offer.expires_at < utc_now():
            offer.status = "expired"
            self.db.commit()
            raise HTTPException(status_code=400, detail="Offer has expired.")

        # Re-check appointment slot availability
        appointment = self.db.scalar(
            select(Appointment).where(Appointment.id == offer.appointment_id).with_for_update()
        )
        if not appointment:
            raise HTTPException(status_code=404, detail="Associated appointment not found.")

        # Confirm booking replacement
        waitlist_entry = self.db.get(WaitlistEntry, offer.waitlist_id)
        if not waitlist_entry:
            raise HTTPException(status_code=404, detail="Waitlist record not found.")

        # Update appointment to new customer details & set scheduled + is_recovery
        appointment.customer_name = waitlist_entry.customer_name
        appointment.customer_email = waitlist_entry.customer_email
        appointment.customer_phone = waitlist_entry.customer_phone
        appointment.status = "scheduled"
        appointment.is_recovery = True

        # Update offer & waitlist status
        offer.status = "accepted"
        offer.accepted_at = utc_now()
        waitlist_entry.status = "fulfilled"

        self.db.commit()
        self.db.refresh(appointment)
        self.db.refresh(offer)

        return {
            "message": "Offer accepted successfully! Your appointment is confirmed.",
            "status": "confirmed",
            "appointment": appointment,
            "offer": offer,
        }

    def withdraw_offer(self, offer_id: str) -> RecoveryOffer:
        offer = self.db.get(RecoveryOffer, offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Offer not found")
        if offer.status == "accepted":
            raise HTTPException(status_code=400, detail="Cannot withdraw an already accepted offer")

        offer.status = "withdrawn"
        waitlist = self.db.get(WaitlistEntry, offer.waitlist_id)
        if waitlist and waitlist.status == "offered":
            waitlist.status = "active"

        self.db.commit()
        self.db.refresh(offer)
        return offer

    def retry_notification(self, notification_id: str) -> NotificationLog:
        log = self.db.get(NotificationLog, notification_id)
        if not log:
            raise HTTPException(status_code=404, detail="Notification log not found")

        if log.retry_count >= 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum notification retry limit (3) exceeded for this offer.",
            )

        log.retry_count += 1

        # Attempt dispatch via provider
        try:
            delivery_result = notification_provider.send_recovery_offer_email(
                recipient_email=log.recipient_email,
                customer_name="Customer",
                service_name="Appointment",
                offer_url=f"/offer/{log.offer_id}",
                expiry_minutes=60,
            )
            log.status = delivery_result.status
            log.error_message = delivery_result.error_message
        except Exception as exc:
            log.status = "failed"
            log.error_message = f"Delivery retry error: {str(exc)}"

        log.sent_at = utc_now()

        # If offer was pending/sent, update sent timestamp
        offer = self.db.get(RecoveryOffer, log.offer_id)
        if offer and offer.status == "pending":
            offer.status = "sent"
            offer.sent_at = utc_now()

        self.db.commit()
        self.db.refresh(log)
        return log

    # ------------------ Metrics & Reports ------------------
    def get_metrics(self) -> MetricsOut:
        # Eligible cancellations: appointments marked as cancelled or that were cancelled and recovered
        eligible_cancellations = (
            self.db.scalar(
                select(func.count(Appointment.id)).where(
                    (Appointment.status == "cancelled") | (Appointment.cancelled_at.is_not(None))
                )
            )
            or 0
        )

        # Recovered appointments: offers accepted
        recovered_appointments = (
            self.db.scalar(
                select(func.count(RecoveryOffer.id)).where(RecoveryOffer.status == "accepted")
            )
            or 0
        )

        recovery_rate = (
            round((recovered_appointments / eligible_cancellations) * 100.0, 1)
            if eligible_cancellations > 0
            else 0.0
        )

        # Median time to refill (minutes from appointment.cancelled_at to offer.accepted_at)
        accepted_offers = list(
            self.db.scalars(
                select(RecoveryOffer)
                .options(joinedload(RecoveryOffer.appointment))
                .where(RecoveryOffer.status == "accepted")
            ).all()
        )
        durations = []
        for o in accepted_offers:
            if o.accepted_at and o.appointment and o.appointment.cancelled_at:
                diff = (o.accepted_at - o.appointment.cancelled_at).total_seconds() / 60.0
                if diff >= 0:
                    durations.append(diff)

        median_time = round(statistics.median(durations), 1) if durations else None

        # Notification failure rate
        total_notifications = self.db.scalar(select(func.count(NotificationLog.id))) or 0
        failed_notifications = (
            self.db.scalar(
                select(func.count(NotificationLog.id)).where(NotificationLog.status == "failed")
            )
            or 0
        )

        notif_fail_rate = (
            round((failed_notifications / total_notifications) * 100.0, 1)
            if total_notifications > 0
            else 0.0
        )

        # Active waitlist count
        total_active_waitlist = (
            self.db.scalar(
                select(func.count(WaitlistEntry.id)).where(WaitlistEntry.status == "active")
            )
            or 0
        )

        # Active offers count
        active_offers_count = (
            self.db.scalar(
                select(func.count(RecoveryOffer.id)).where(
                    RecoveryOffer.status.in_(["pending", "sent"]),
                    RecoveryOffer.expires_at > utc_now(),
                )
            )
            or 0
        )

        return MetricsOut(
            eligible_cancellations=eligible_cancellations,
            recovered_appointments=recovered_appointments,
            recovery_rate=recovery_rate,
            time_to_refill_median_minutes=median_time,
            notification_failure_rate=notif_fail_rate,
            total_active_waitlist=total_active_waitlist,
            active_offers_count=active_offers_count,
            period="all_time",
        )

    # ------------------ Settings ------------------
    def get_or_create_settings(self) -> BusinessSetting:
        setting = self.db.get(BusinessSetting, 1)
        if not setting:
            setting = BusinessSetting(
                id=1,
                business_name="SlotBack Service Studio",
                default_offer_expiry_minutes=60,
                notification_email="staff@slotback.com",
                auto_match_waitlist=True,
            )
            self.db.add(setting)
            self.db.commit()
            self.db.refresh(setting)
        return setting

    def update_settings(self, data: BusinessSettingBase) -> BusinessSetting:
        setting = self.get_or_create_settings()
        setting.business_name = data.business_name
        setting.default_offer_expiry_minutes = data.default_offer_expiry_minutes
        setting.notification_email = data.notification_email
        setting.auto_match_waitlist = data.auto_match_waitlist
        setting.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(setting)
        return setting
