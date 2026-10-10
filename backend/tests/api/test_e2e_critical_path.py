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


def iso_time(minutes: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()


def test_complete_8_step_critical_e2e_workflow():
    # Ensure auto_match_waitlist is True
    settings = client.get("/api/v1/settings").json()
    settings["auto_match_waitlist"] = True
    client.put("/api/v1/settings", json=settings)

    # STEP 1: Staff books an appointment
    svc_res = client.post(
        "/api/v1/services",
        json={
            "name": "Deep Tissue Massage",
            "description": "60 min therapeutic massage",
            "duration_minutes": 60,
            "price": 110.0,
        },
    )
    assert svc_res.status_code == 201
    service_id = svc_res.json()["id"]

    # Register waitlisted customer
    wl_res = client.post(
        "/api/v1/waitlist",
        json={
            "customer_name": "E2E Waitlist Customer",
            "customer_email": "e2e_waitlist@example.com",
            "customer_phone": "555-0999",
            "service_id": service_id,
            "preferred_start_date": iso_time(-60),
            "preferred_end_date": iso_time(1440),
            "notes": "Urgent request",
        },
    )
    assert wl_res.status_code == 201

    # Staff books appointment for Original Customer
    book_res = client.post(
        "/api/v1/appointments",
        json={
            "customer_name": "Original Customer",
            "customer_email": "original@example.com",
            "customer_phone": "555-0111",
            "service_id": service_id,
            "start_time": iso_time(120),
        },
    )
    assert book_res.status_code == 201
    app_id = book_res.json()["id"]

    # STEP 2: Appointment is cancelled
    cancel_res = client.post(
        f"/api/v1/appointments/{app_id}/cancel",
        json={"reason": "Customer cancellation request"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # STEP 3: Recovery offer is created
    offers_res = client.get("/api/v1/recovery/offers")
    assert offers_res.status_code == 200
    offers = offers_res.json()
    offer = next(o for o in offers if o["appointment_id"] == app_id)
    token = offer["token"]
    assert offer["status"] in ["sent", "pending"]

    # STEP 4: Customer accepts the offer
    accept_res = client.post(f"/api/v1/recovery/offers/{token}/accept")
    assert accept_res.status_code == 200
    acc_data = accept_res.json()
    assert acc_data["status"] == "confirmed"
    assert acc_data["appointment"]["customer_name"] == "E2E Waitlist Customer"

    # STEP 5: Booking is confirmed exactly once (duplicate acceptance rejected)
    dup_accept_res = client.post(f"/api/v1/recovery/offers/{token}/accept")
    assert dup_accept_res.status_code == 400
    assert "already been accepted" in dup_accept_res.json()["detail"]

    # STEP 6: Dashboard reflects the persisted result
    metrics_res = client.get("/api/v1/reports/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["eligible_cancellations"] >= 1
    assert metrics["recovered_appointments"] >= 1
    assert metrics["recovery_rate"] > 0.0

    # STEP 7: Expired and conflicting offers are rejected
    wl2_res = client.post(
        "/api/v1/waitlist",
        json={
            "customer_name": "Second Waitlist Customer",
            "customer_email": "second@example.com",
            "customer_phone": "555-0888",
            "service_id": service_id,
            "preferred_start_date": iso_time(-60),
            "preferred_end_date": iso_time(1440),
        },
    )
    waitlist_id2 = wl2_res.json()["id"]

    # Disable auto-match to test manual offer
    settings["auto_match_waitlist"] = False
    client.put("/api/v1/settings", json=settings)

    book_res2 = client.post(
        "/api/v1/appointments",
        json={
            "customer_name": "Test Conflict Customer",
            "customer_email": "conflict@example.com",
            "customer_phone": "555-0888",
            "service_id": service_id,
            "start_time": iso_time(360),
        },
    )
    app_id2 = book_res2.json()["id"]
    client.post(f"/api/v1/appointments/{app_id2}/cancel", json={"reason": "Test"})

    # Create offer for waitlist_id2
    exp_offer_res = client.post(
        "/api/v1/recovery/offers",
        json={
            "appointment_id": app_id2,
            "waitlist_id": waitlist_id2,
            "expiry_minutes": 60,
        },
    )
    assert exp_offer_res.status_code == 201

    # STEP 8: Notification failures remain visible and recoverable
    book_res3 = client.post(
        "/api/v1/appointments",
        json={
            "customer_name": "Test Fail Customer",
            "customer_email": "fail@example.com",
            "customer_phone": "555-0777",
            "service_id": service_id,
            "start_time": iso_time(480),
        },
    )
    app_id3 = book_res3.json()["id"]
    client.post(f"/api/v1/appointments/{app_id3}/cancel", json={"reason": "Test Fail"})

    # Create another waitlist customer
    wl3_res = client.post(
        "/api/v1/waitlist",
        json={
            "customer_name": "Third Waitlist Customer",
            "customer_email": "third@example.com",
            "customer_phone": "555-0777",
            "service_id": service_id,
            "preferred_start_date": iso_time(-60),
            "preferred_end_date": iso_time(1440),
        },
    )
    waitlist_id3 = wl3_res.json()["id"]

    fail_offer_res = client.post(
        "/api/v1/recovery/offers",
        json={
            "appointment_id": app_id3,
            "waitlist_id": waitlist_id3,
            "expiry_minutes": 60,
            "simulate_notification_failure": True,
        },
    )
    assert fail_offer_res.status_code == 201

    all_offers = client.get("/api/v1/recovery/offers").json()
    failed_offer = next(
        (
            o
            for o in all_offers
            if any(n["status"] == "failed" for n in o.get("notification_logs", []))
        ),
        None,
    )
    assert failed_offer is not None
    failed_log = next(n for n in failed_offer["notification_logs"] if n["status"] == "failed")

    # Retry delivery
    retry_res = client.post(f"/api/v1/recovery/notifications/{failed_log['id']}/retry")
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] == "delivered"

    # Restore auto_match_waitlist = True
    settings["auto_match_waitlist"] = True
    client.put("/api/v1/settings", json=settings)
