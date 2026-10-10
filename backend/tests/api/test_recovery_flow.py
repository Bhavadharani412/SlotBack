from datetime import UTC, datetime, timedelta

import pytest
from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def authenticate_client(admin_headers):
    client.headers.update(admin_headers)
    yield
    client.headers.pop("Authorization", None)


def utc_now_iso(minutes_offset: int = 0) -> str:
    dt = datetime.now(UTC) + timedelta(minutes=minutes_offset)
    return dt.isoformat()


def test_full_cancellation_to_recovery_workflow():
    # Ensure settings auto_match is enabled
    settings = client.get("/api/v1/settings").json()
    settings["auto_match_waitlist"] = True
    client.put("/api/v1/settings", json=settings)

    # 1. Create a service
    res = client.post(
        "/api/v1/services",
        json={
            "name": "Swedish Massage 60",
            "description": "Full body relaxation massage",
            "duration_minutes": 60,
            "price": 95.0,
        },
    )
    assert res.status_code == 201
    service = res.json()
    service_id = service["id"]

    # 2. Add a customer to waitlist
    res = client.post(
        "/api/v1/waitlist",
        json={
            "customer_name": "Alice Waitlist",
            "customer_email": "alice@example.com",
            "customer_phone": "555-0199",
            "service_id": service_id,
            "preferred_start_date": utc_now_iso(-120),
            "preferred_end_date": utc_now_iso(1440),
            "notes": "Prefers morning slots",
        },
    )
    assert res.status_code == 201
    waitlist_entry = res.json()
    waitlist_id = waitlist_entry["id"]

    # 3. Create initial appointment for Bob
    start_time = utc_now_iso(180)  # in 3 hours
    res = client.post(
        "/api/v1/appointments",
        json={
            "customer_name": "Bob Original",
            "customer_email": "bob@example.com",
            "customer_phone": "555-0122",
            "service_id": service_id,
            "start_time": start_time,
        },
    )
    assert res.status_code == 201
    appointment = res.json()
    appointment_id = appointment["id"]

    # 4. Cancel Bob's appointment (triggers recovery offer generation for Alice)
    res = client.post(
        f"/api/v1/appointments/{appointment_id}/cancel",
        json={"reason": "Sudden meeting schedule change"},
    )
    assert res.status_code == 200
    cancelled_app = res.json()
    assert cancelled_app["status"] == "cancelled"

    # 5. Check recovery offers list
    res = client.get("/api/v1/recovery/offers")
    assert res.status_code == 200
    offers = res.json()
    assert len(offers) >= 1

    offer = next(o for o in offers if o["appointment_id"] == appointment_id)
    assert offer["status"] in ["sent", "pending"]
    assert offer["waitlist_id"] == waitlist_id
    offer_token = offer["token"]

    # 6. Customer (Alice) accepts the recovery offer
    res = client.post(f"/api/v1/recovery/offers/{offer_token}/accept")
    assert res.status_code == 200
    accept_resp = res.json()
    assert accept_resp["status"] == "confirmed"
    assert accept_resp["appointment"]["customer_name"] == "Alice Waitlist"
    assert accept_resp["appointment"]["is_recovery"] is True

    # 7. Attempt duplicate acceptance (must be rejected)
    res = client.post(f"/api/v1/recovery/offers/{offer_token}/accept")
    assert res.status_code == 400
    assert "already been accepted" in res.json()["detail"]

    # 8. Check metrics endpoints to confirm persisted recovery outcome
    res = client.get("/api/v1/reports/metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert metrics["eligible_cancellations"] >= 1
    assert metrics["recovered_appointments"] >= 1
    assert metrics["recovery_rate"] > 0.0


def test_notification_failure_and_retry():
    # Disable auto-match to manually issue offer with failure simulation
    settings = client.get("/api/v1/settings").json()
    settings["auto_match_waitlist"] = False
    client.put("/api/v1/settings", json=settings)

    # Create service
    res = client.post(
        "/api/v1/services",
        json={
            "name": "Facial Treatment",
            "description": "Deep cleansing facial",
            "duration_minutes": 45,
            "price": 80.0,
        },
    )
    service_id = res.json()["id"]

    # Create waitlist entry
    res = client.post(
        "/api/v1/waitlist",
        json={
            "customer_name": "Charlie Failed",
            "customer_email": "charlie@example.com",
            "customer_phone": "555-0333",
            "service_id": service_id,
            "preferred_start_date": utc_now_iso(-10),
            "preferred_end_date": utc_now_iso(500),
        },
    )
    waitlist_id = res.json()["id"]

    # Create appointment
    res = client.post(
        "/api/v1/appointments",
        json={
            "customer_name": "David Cancelled",
            "customer_email": "david@example.com",
            "customer_phone": "555-0444",
            "service_id": service_id,
            "start_time": utc_now_iso(300),
        },
    )
    app_id = res.json()["id"]

    client.post(f"/api/v1/appointments/{app_id}/cancel", json={"reason": "Sick"})

    # Explicitly create offer with simulated notification failure
    res_offer = client.post(
        "/api/v1/recovery/offers",
        json={
            "appointment_id": app_id,
            "waitlist_id": waitlist_id,
            "expiry_minutes": 30,
            "simulate_notification_failure": True,
        },
    )
    assert res_offer.status_code == 201
    failed_offer = res_offer.json()

    failed_log = next(n for n in failed_offer["notification_logs"] if n["status"] == "failed")
    log_id = failed_log["id"]

    # Retry notification delivery
    res_retry = client.post(f"/api/v1/recovery/notifications/{log_id}/retry")
    assert res_retry.status_code == 200
    assert res_retry.json()["status"] == "delivered"

    # Restore auto_match
    settings["auto_match_waitlist"] = True
    client.put("/api/v1/settings", json=settings)


def test_ineligible_waitlist_customer_rejected_even_if_manipulated_request():
    """
    Regression test: verify that even if a manipulated request is sent directly to
    POST /api/v1/recovery/offers, an ineligible waitlist customer cannot receive an offer.
    """
    # 1. Create two distinct services
    res_svc1 = client.post(
        "/api/v1/services",
        json={"name": "Aromatherapy Massage", "duration_minutes": 60, "price": 100.0},
    )
    svc1_id = res_svc1.json()["id"]

    res_svc2 = client.post(
        "/api/v1/services",
        json={"name": "Hot Stone Massage", "duration_minutes": 90, "price": 130.0},
    )
    svc2_id = res_svc2.json()["id"]

    # 2. Customer 1 on waitlist for Service 2 (wrong service)
    res_wl_wrong_svc = client.post(
        "/api/v1/waitlist",
        json={
            "customer_name": "Wrong Service Customer",
            "customer_email": "wrong_svc@example.com",
            "customer_phone": "555-1111",
            "service_id": svc2_id,
            "preferred_start_date": utc_now_iso(-60),
            "preferred_end_date": utc_now_iso(1440),
        },
    )
    wl_wrong_svc_id = res_wl_wrong_svc.json()["id"]

    # 3. Customer 2 on waitlist for Service 1 but preferred date window is in future (wrong date window)
    res_wl_wrong_date = client.post(
        "/api/v1/waitlist",
        json={
            "customer_name": "Wrong Date Customer",
            "customer_email": "wrong_date@example.com",
            "customer_phone": "555-2222",
            "service_id": svc1_id,
            "preferred_start_date": utc_now_iso(2880),  # starts in 2 days
            "preferred_end_date": utc_now_iso(4320),  # ends in 3 days
        },
    )
    wl_wrong_date_id = res_wl_wrong_date.json()["id"]

    # 4. Appointment for Service 1 is scheduled for 3 hours from now and cancelled
    res_appt = client.post(
        "/api/v1/appointments",
        json={
            "customer_name": "Cancelled Client",
            "customer_email": "cancelled@example.com",
            "customer_phone": "555-3333",
            "service_id": svc1_id,
            "start_time": utc_now_iso(180),
        },
    )
    appt_id = res_appt.json()["id"]
    client.post(f"/api/v1/appointments/{appt_id}/cancel", json={"reason": "Emergency"})

    # 5. Manipulated request A: Attempt to issue offer to Customer 1 (wrong service)
    res_offer_wrong_svc = client.post(
        "/api/v1/recovery/offers",
        json={
            "appointment_id": appt_id,
            "waitlist_id": wl_wrong_svc_id,
            "expiry_minutes": 60,
        },
    )
    assert res_offer_wrong_svc.status_code == 400
    assert "service mismatch" in res_offer_wrong_svc.json()["detail"].lower()

    # 6. Manipulated request B: Attempt to issue offer to Customer 2 (outside date window)
    res_offer_wrong_date = client.post(
        "/api/v1/recovery/offers",
        json={
            "appointment_id": appt_id,
            "waitlist_id": wl_wrong_date_id,
            "expiry_minutes": 60,
        },
    )
    assert res_offer_wrong_date.status_code == 400
    assert (
        "outside" in res_offer_wrong_date.json()["detail"].lower()
        or "window" in res_offer_wrong_date.json()["detail"].lower()
    )


def test_timezone_aware_date_matching_and_booking():
    """
    Verify that ISO strings with distinct timezone offsets (+05:30, -04:00, Z)
    are handled accurately without offset-comparison runtime errors.
    """
    res_svc = client.post(
        "/api/v1/services",
        json={"name": "Express Manicure", "duration_minutes": 30, "price": 40.0},
    )
    svc_id = res_svc.json()["id"]

    # Appointment with UTC offset: 2026-10-15T10:00:00+05:30
    appt_start_offset = "2026-10-15T10:00:00+05:30"
    res_appt = client.post(
        "/api/v1/appointments",
        json={
            "customer_name": "Timezone User",
            "customer_email": "tz@example.com",
            "customer_phone": "555-9999",
            "service_id": svc_id,
            "start_time": appt_start_offset,
        },
    )
    assert res_appt.status_code == 201
    appt_data = res_appt.json()
    assert appt_data["status"] == "scheduled"


def test_overlapping_booking_conflict_prevention():
    """Verify that attempting to book an overlapping time slot for the same service returns 409 Conflict."""
    res_svc = client.post(
        "/api/v1/services",
        json={"name": "Acupuncture 60", "duration_minutes": 60, "price": 90.0},
    )
    svc_id = res_svc.json()["id"]

    start_time = utc_now_iso(120)
    # First booking
    res1 = client.post(
        "/api/v1/appointments",
        json={
            "customer_name": "First Booking",
            "customer_email": "first@example.com",
            "customer_phone": "555-0101",
            "service_id": svc_id,
            "start_time": start_time,
        },
    )
    assert res1.status_code == 201

    # Overlapping second booking (30 mins later, within 60 min duration)
    overlap_time = utc_now_iso(150)
    res2 = client.post(
        "/api/v1/appointments",
        json={
            "customer_name": "Second Booking (Conflict)",
            "customer_email": "second@example.com",
            "customer_phone": "555-0102",
            "service_id": svc_id,
            "start_time": overlap_time,
        },
    )
    assert res2.status_code == 409
    assert "already booked" in res2.json()["detail"].lower()
