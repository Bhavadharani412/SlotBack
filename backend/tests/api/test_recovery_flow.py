from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

def utc_now_iso(minutes_offset: int = 0) -> str:
    dt = datetime.now(timezone.utc) + timedelta(minutes=minutes_offset)
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
