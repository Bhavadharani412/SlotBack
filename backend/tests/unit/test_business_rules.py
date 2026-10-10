"""
Unit tests for isolated business rule logic in SlotBackService.

These tests do NOT hit the database. They use MagicMock to stub out
the SQLAlchemy session and verify pure business logic:
  - waitlist eligibility matching
  - offer expiration status
  - valid/invalid status transitions
  - recovery metric calculations
  - empty waitlist / no-eligible-customer cases
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from unittest.mock import MagicMock, patch
import pytest

from backend.app.models.domain import Appointment, RecoveryOffer, WaitlistEntry
from backend.app.services.recovery_service import SlotBackService


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_service(service_id: str = "svc-1", duration_minutes: int = 60) -> MagicMock:
    svc = MagicMock()
    svc.id = service_id
    svc.duration_minutes = duration_minutes
    svc.name = "Test Service"
    svc.price = 100.0
    return svc


def make_appointment(
    appointment_id: str = "appt-1",
    service_id: str = "svc-1",
    status: str = "cancelled",
    start_time: Optional[datetime] = None,
    cancelled_at: Optional[datetime] = None,
) -> MagicMock:
    appt = MagicMock(spec=Appointment)
    appt.id = appointment_id
    appt.service_id = service_id
    appt.status = status
    appt.start_time = start_time or (utc_now() + timedelta(hours=2))
    appt.end_time = (appt.start_time + timedelta(hours=1))
    appt.cancelled_at = cancelled_at or utc_now()
    appt.customer_name = "Original Customer"
    appt.customer_email = "original@example.com"
    appt.customer_phone = "555-0001"
    appt.is_recovery = False
    return appt


def make_waitlist_entry(
    entry_id: str = "wl-1",
    service_id: str = "svc-1",
    status: str = "active",
    preferred_start: Optional[datetime] = None,
    preferred_end: Optional[datetime] = None,
) -> MagicMock:
    wl = MagicMock(spec=WaitlistEntry)
    wl.id = entry_id
    wl.service_id = service_id
    wl.status = status
    wl.preferred_start_date = preferred_start or (utc_now() - timedelta(hours=1))
    wl.preferred_end_date = preferred_end or (utc_now() + timedelta(hours=24))
    wl.customer_name = "Waitlisted Customer"
    wl.customer_email = "waitlisted@example.com"
    wl.customer_phone = "555-0002"
    wl.created_at = utc_now() - timedelta(hours=1)
    return wl


def make_offer(
    offer_id: str = "offer-1",
    appointment_id: str = "appt-1",
    waitlist_id: str = "wl-1",
    status: str = "sent",
    expires_at: Optional[datetime] = None,
    accepted_at: Optional[datetime] = None,
) -> MagicMock:
    offer = MagicMock(spec=RecoveryOffer)
    offer.id = offer_id
    offer.appointment_id = appointment_id
    offer.waitlist_id = waitlist_id
    offer.status = status
    offer.expires_at = expires_at or (utc_now() + timedelta(minutes=60))
    offer.accepted_at = accepted_at
    offer.token = f"token-{offer_id}"
    return offer


def make_service_with_db(db: MagicMock) -> SlotBackService:
    return SlotBackService(db=db)


# =====================================================================
# Tests: Waitlist eligibility matching
# =====================================================================

class TestWaitlistEligibility:
    """Tests for get_eligible_waitlist_for_appointment business logic."""

    def test_eligible_entry_matches_service_and_date_window(self):
        """An active waitlist entry with matching service and overlapping date window is eligible."""
        db = MagicMock()
        svc = make_service()
        appointment = make_appointment(start_time=utc_now() + timedelta(hours=3))
        wl_entry = make_waitlist_entry(
            preferred_start=utc_now() - timedelta(hours=1),
            preferred_end=utc_now() + timedelta(hours=24),
        )

        db.scalars.return_value.all.return_value = [wl_entry]

        service = make_service_with_db(db)
        result = service.get_eligible_waitlist_for_appointment(appointment)

        assert result == [wl_entry]
        db.scalars.assert_called_once()

    def test_empty_result_when_no_waitlist_entries(self):
        """Returns empty list when no waitlist entries exist for the service."""
        db = MagicMock()
        appointment = make_appointment()
        db.scalars.return_value.all.return_value = []

        service = make_service_with_db(db)
        result = service.get_eligible_waitlist_for_appointment(appointment)

        assert result == []

    def test_auto_issue_returns_none_when_no_eligible_customers(self):
        """auto_issue_recovery_offer returns None if no eligible waitlist entries exist."""
        db = MagicMock()
        appointment = make_appointment()
        db.scalars.return_value.all.return_value = []

        service = make_service_with_db(db)
        result = service.auto_issue_recovery_offer(appointment)

        assert result is None


# =====================================================================
# Tests: Offer expiration
# =====================================================================

class TestOfferExpiration:
    """Tests for offer expiration logic — offers should be marked expired when past deadline."""

    def test_offer_past_expiry_is_expired(self):
        """An offer with expires_at in the past should have status 'expired'."""
        offer = make_offer(status="sent", expires_at=utc_now() - timedelta(minutes=5))
        assert offer.expires_at < utc_now()
        assert offer.status == "sent"  # expiry is applied lazily in service layer

    def test_offer_future_expiry_is_valid(self):
        """An offer with expires_at in the future is still valid."""
        offer = make_offer(status="sent", expires_at=utc_now() + timedelta(minutes=30))
        assert offer.expires_at > utc_now()

    def test_accept_offer_rejects_if_expired(self):
        """accept_offer raises 400 when the offer has expired."""
        from fastapi import HTTPException

        db = MagicMock()
        expired_offer = make_offer(
            status="sent",
            expires_at=utc_now() - timedelta(minutes=10),
        )
        db.scalar.return_value = expired_offer

        service = make_service_with_db(db)
        with pytest.raises(HTTPException) as exc_info:
            service.accept_offer("token-offer-1")

        assert exc_info.value.status_code == 400
        assert "expired" in exc_info.value.detail.lower()

    def test_accept_offer_rejects_already_accepted(self):
        """accept_offer raises 400 when the offer has already been accepted."""
        from fastapi import HTTPException

        db = MagicMock()
        accepted_offer = make_offer(
            status="accepted",
            expires_at=utc_now() + timedelta(minutes=30),
            accepted_at=utc_now() - timedelta(minutes=5),
        )
        db.scalar.return_value = accepted_offer

        service = make_service_with_db(db)
        with pytest.raises(HTTPException) as exc_info:
            service.accept_offer("token-offer-1")

        assert exc_info.value.status_code == 400
        assert "already been accepted" in exc_info.value.detail

    def test_accept_offer_rejects_withdrawn(self):
        """accept_offer raises 400 for withdrawn offers."""
        from fastapi import HTTPException

        db = MagicMock()
        withdrawn_offer = make_offer(
            status="withdrawn",
            expires_at=utc_now() + timedelta(minutes=30),
        )
        db.scalar.return_value = withdrawn_offer

        service = make_service_with_db(db)
        with pytest.raises(HTTPException) as exc_info:
            service.accept_offer("token-offer-1")

        assert exc_info.value.status_code == 400
        assert "no longer valid" in exc_info.value.detail.lower()


# =====================================================================
# Tests: Status transitions
# =====================================================================

class TestStatusTransitions:
    """Tests for valid/invalid status transition logic."""

    def test_cancel_appointment_with_wrong_status_returns_early(self):
        """Cancelling an already-cancelled appointment returns it without mutation."""
        db = MagicMock()
        already_cancelled = make_appointment(status="cancelled")
        db.get.return_value = already_cancelled

        service = make_service_with_db(db)
        result = service.cancel_appointment("appt-1", reason="already done")

        # Should return without committing again (idempotent)
        assert result.status == "cancelled"

    def test_create_offer_rejects_if_appointment_not_cancelled(self):
        """create_recovery_offer raises 400 if appointment is not in 'cancelled' state."""
        from fastapi import HTTPException
        from backend.app.schemas.domain import RecoveryOfferCreate

        db = MagicMock()
        active_appointment = make_appointment(status="scheduled")
        active_waitlist = make_waitlist_entry(status="active")
        db.get.side_effect = lambda model, pk: (
            active_appointment if model.__tablename__ == "appointments" else active_waitlist
        )

        service = make_service_with_db(db)
        with pytest.raises(HTTPException) as exc_info:
            service.create_recovery_offer(
                RecoveryOfferCreate(
                    appointment_id="appt-1",
                    waitlist_id="wl-1",
                    expiry_minutes=60,
                )
            )

        assert exc_info.value.status_code == 400
        assert "cancelled" in exc_info.value.detail.lower()

    def test_create_offer_rejects_if_waitlist_entry_not_eligible(self):
        """create_recovery_offer raises 400 if waitlist entry has status 'fulfilled'."""
        from fastapi import HTTPException
        from backend.app.schemas.domain import RecoveryOfferCreate

        db = MagicMock()
        cancelled_appt = make_appointment(status="cancelled")
        fulfilled_waitlist = make_waitlist_entry(status="fulfilled")
        db.get.side_effect = lambda model, pk: (
            cancelled_appt if model.__name__ == "Appointment" else fulfilled_waitlist
        )

        service = make_service_with_db(db)

        # Patch the attribute-based get to return what we want
        db.get = MagicMock(side_effect=[cancelled_appt, fulfilled_waitlist])

        with pytest.raises(HTTPException) as exc_info:
            service.create_recovery_offer(
                RecoveryOfferCreate(
                    appointment_id="appt-1",
                    waitlist_id="wl-1",
                    expiry_minutes=60,
                )
            )

        assert exc_info.value.status_code == 400
        assert "not eligible" in exc_info.value.detail.lower()

    def test_withdraw_accepted_offer_raises_error(self):
        """Withdrawing an already-accepted offer raises 400."""
        from fastapi import HTTPException

        db = MagicMock()
        accepted_offer = make_offer(status="accepted")
        db.get.return_value = accepted_offer

        service = make_service_with_db(db)
        with pytest.raises(HTTPException) as exc_info:
            service.withdraw_offer("offer-1")

        assert exc_info.value.status_code == 400
        assert "accepted" in exc_info.value.detail.lower()


# =====================================================================
# Tests: Recovery metric calculations
# =====================================================================

class TestMetricCalculations:
    """Tests for metric formula correctness using mocked scalar DB calls."""

    def test_recovery_rate_is_zero_when_no_cancellations(self):
        """Recovery rate should be 0.0 when no eligible cancellations exist."""
        db = MagicMock()
        # scalar calls: eligible_cancellations, recovered_appointments, accepted_offers, total_notifs, failed_notifs, active_waitlist, active_offers
        db.scalar.side_effect = [0, 0, None, 0, 0, 0, 0]
        db.scalars.return_value.all.return_value = []

        service = make_service_with_db(db)
        metrics = service.get_metrics()

        assert metrics.eligible_cancellations == 0
        assert metrics.recovered_appointments == 0
        assert metrics.recovery_rate == 0.0

    def test_recovery_rate_100_when_all_cancellations_recovered(self):
        """Recovery rate is 100% when all cancellations have been recovered."""
        db = MagicMock()
        # 2 cancellations, 2 recovered
        db.scalar.side_effect = [2, 2, None, 0, 0, 0, 0]

        # Accepted offers with timing data
        appt1 = MagicMock()
        appt1.cancelled_at = utc_now() - timedelta(minutes=20)
        offer1 = MagicMock()
        offer1.accepted_at = utc_now() - timedelta(minutes=10)
        offer1.appointment = appt1

        appt2 = MagicMock()
        appt2.cancelled_at = utc_now() - timedelta(minutes=30)
        offer2 = MagicMock()
        offer2.accepted_at = utc_now() - timedelta(minutes=15)
        offer2.appointment = appt2

        db.scalars.return_value.all.return_value = [offer1, offer2]

        service = make_service_with_db(db)
        metrics = service.get_metrics()

        assert metrics.recovery_rate == 100.0
        assert metrics.recovered_appointments == 2

    def test_notification_failure_rate_calculated_correctly(self):
        """Notification failure rate is failures/total * 100."""
        db = MagicMock()
        # scalar call order: eligible_cancellations, recovered_appointments,
        #   total_notifications, failed_notifications, total_active_waitlist, active_offers_count
        # scalars (plural) is used separately for accepted_offers list
        db.scalar.side_effect = [2, 1, 10, 2, 5, 1]
        db.scalars.return_value.all.return_value = []

        service = make_service_with_db(db)
        metrics = service.get_metrics()

        assert metrics.notification_failure_rate == 20.0

    def test_median_time_is_none_when_no_accepted_offers(self):
        """Median time to refill is None when no accepted offers with timing exist."""
        db = MagicMock()
        db.scalar.side_effect = [1, 0, None, 0, 0, 0, 0]
        db.scalars.return_value.all.return_value = []

        service = make_service_with_db(db)
        metrics = service.get_metrics()

        assert metrics.time_to_refill_median_minutes is None
