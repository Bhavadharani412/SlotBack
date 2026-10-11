from datetime import UTC, datetime, timedelta

import pytest
from backend.app.core.auth import ensure_initial_admin
from backend.app.core.config import Settings, settings
from backend.app.core.security import create_access_token
from backend.app.main import app
from backend.app.models.domain import User
from backend.tests.conftest import TestingSessionLocal
from fastapi.testclient import TestClient

client = TestClient(app)


def test_anonymous_requests_cannot_access_staff_endpoints():
    """Verify that unauthenticated anonymous calls to staff endpoints are rejected with 401."""
    # 1. Staff endpoints must return 401 Unauthorized
    assert client.get("/api/v1/appointments").status_code == 401
    assert client.get("/api/v1/waitlist").status_code == 401
    assert client.get("/api/v1/recovery/offers").status_code == 401
    assert client.get("/api/v1/reports/metrics").status_code == 401
    assert client.get("/api/v1/settings").status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/appointments/any-id/cancel", json={}).status_code == 401
    assert client.post("/api/v1/recovery/offers", json={"appointment_id": "1", "waitlist_id": "1"}).status_code == 401


def test_initial_admin_requires_configured_password(monkeypatch):
    monkeypatch.setattr(settings, "initial_admin_password", "")
    with TestingSessionLocal() as session:
        session.query(User).delete()
        session.flush()
        with pytest.raises(RuntimeError, match="INITIAL_ADMIN_PASSWORD must be configured"):
            ensure_initial_admin(session)
        session.rollback()
        assert session.query(User).count() == 1


def test_public_customer_flows_work_without_authentication(admin_headers):
    """Verify that customer booking and capability-token offer flows function without credentials."""
    # Create service using admin
    svc = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"name": "Public Haircut", "duration_minutes": 30, "price": 40.0},
    ).json()

    # Public active services query (no auth headers)
    res_services = client.get("/api/v1/services?active_only=true")
    assert res_services.status_code == 200
    assert any(s["id"] == svc["id"] for s in res_services.json())

    # Public appointment booking (no auth headers)
    start_time = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    res_booking = client.post(
        "/api/v1/appointments",
        json={
            "customer_name": "Public Customer",
            "customer_email": "public@example.com",
            "customer_phone": "555-1234",
            "service_id": svc["id"],
            "start_time": start_time,
        },
    )
    assert res_booking.status_code == 201

    # Public waitlist join (no auth headers)
    res_waitlist = client.post(
        "/api/v1/waitlist",
        json={
            "customer_name": "Waitlist Customer",
            "customer_email": "waitlist@example.com",
            "customer_phone": "555-5678",
            "service_id": svc["id"],
            "preferred_start_date": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "preferred_end_date": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
    )
    assert res_waitlist.status_code == 201


def test_staff_login_and_permitted_operations(admin_headers, staff_headers):
    """Verify that staff can log in and perform permitted operational actions."""
    # Login via /auth/login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": settings.initial_admin_email, "password": settings.initial_admin_password},
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "admin"

    # Authenticated staff can read appointments, waitlist, metrics
    assert client.get("/api/v1/appointments", headers=staff_headers).status_code == 200
    assert client.get("/api/v1/waitlist", headers=staff_headers).status_code == 200
    assert client.get("/api/v1/recovery/offers", headers=staff_headers).status_code == 200
    assert client.get("/api/v1/reports/metrics", headers=staff_headers).status_code == 200
    assert client.get("/api/v1/settings", headers=staff_headers).status_code == 200


def test_role_based_access_control_staff_vs_admin(admin_headers, staff_headers):
    """Verify RBAC: non-admin staff are forbidden (403) from administrative actions."""
    # Non-admin staff cannot create services (403)
    res_create_svc = client.post(
        "/api/v1/services",
        headers=staff_headers,
        json={"name": "Forbidden Service", "duration_minutes": 30, "price": 50.0},
    )
    assert res_create_svc.status_code == 403
    assert "Administrator privileges required" in res_create_svc.json()["detail"]

    # Non-admin staff cannot update settings (403)
    res_update_settings = client.put(
        "/api/v1/settings",
        headers=staff_headers,
        json={
            "business_name": "Hacked Name",
            "default_offer_expiry_minutes": 30,
            "notification_email": "hack@example.com",
            "auto_match_waitlist": False,
        },
    )
    assert res_update_settings.status_code == 403

    # Non-admin staff cannot create new staff users (403)
    res_create_user = client.post(
        "/api/v1/auth/users",
        headers=staff_headers,
        json={
            "email": "newstaff@slotback.com",
            "password": "Password123!",
            "full_name": "New Staff",
            "role": "staff",
        },
    )
    assert res_create_user.status_code == 403

    # Admin CAN create services, update settings, and create users
    res_admin_svc = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"name": "Admin Service", "duration_minutes": 30, "price": 50.0},
    )
    assert res_admin_svc.status_code == 201

    res_admin_user = client.post(
        "/api/v1/auth/users",
        headers=admin_headers,
        json={
            "email": "created.staff@slotback.com",
            "password": "StaffPassword123!",
            "full_name": "Created Staff",
            "role": "staff",
        },
    )
    assert res_admin_user.status_code == 201


def test_invalid_expired_and_malformed_tokens_rejected():
    """Verify that invalid, expired, and fabricated JWTs return 401."""
    # 1. Bogus token
    res_bogus = client.get(
        "/api/v1/appointments",
        headers={"Authorization": "Bearer bogus-token-12345"},
    )
    assert res_bogus.status_code == 401
    assert "Invalid authentication token" in res_bogus.json()["detail"]

    # 2. Expired token
    expired_token = create_access_token(
        data={"sub": "some-id", "email": "test@slotback.com", "role": "admin"},
        expires_delta=timedelta(seconds=-10),
    )
    res_expired = client.get(
        "/api/v1/appointments",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res_expired.status_code == 401
    assert "token has expired" in res_expired.json()["detail"]


def test_rate_limiting_on_login_endpoint():
    """Verify that exceeding rate limits returns HTTP 429 Too Many Requests with Retry-After header."""
    # /api/v1/auth/login is limited to 10 requests / 60 seconds
    for _ in range(10):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpassword"},
        )
        assert res.status_code in (401, 200)

    # 11th request must trigger rate limiter (429)
    res_blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert res_blocked.status_code == 429
    assert "Rate limit exceeded" in res_blocked.json()["detail"]
    assert "retry-after" in res_blocked.headers


def test_production_configuration_fail_safe_guards():
    """Verify that Settings.validate_production_configuration raises ValueError on insecure setups."""
    # 1. Insecure default SECRET_KEY in production raises error
    insecure_settings = Settings(
        app_env="production",
        debug=False,
        secret_key="slotback-insecure-dev-secret-key-change-in-production-min32chars",
        database_url="postgresql+psycopg://slotback:pw@localhost/slotback",
        cors_origins="https://slotback.com",
    )
    with pytest.raises(ValueError, match="SECRET_KEY must be a unique, high-entropy string"):
        insecure_settings.validate_production_configuration()

    # 2. DEBUG=True in production raises error
    debug_settings = Settings(
        app_env="production",
        debug=True,
        secret_key="super-secure-production-secret-key-with-high-entropy-123456",
        database_url="postgresql+psycopg://slotback:pw@localhost/slotback",
        cors_origins="https://slotback.com",
    )
    with pytest.raises(ValueError, match="DEBUG must be false in production"):
        debug_settings.validate_production_configuration()

    # 3. Wildcard CORS in production raises error
    wildcard_cors_settings = Settings(
        app_env="production",
        debug=False,
        secret_key="super-secure-production-secret-key-with-high-entropy-123456",
        database_url="postgresql+psycopg://slotback:pw@localhost/slotback",
        cors_origins="*",
    )
    with pytest.raises(ValueError, match="Wildcard CORS"):
        wildcard_cors_settings.validate_production_configuration()

    # 4. Valid production settings pass
    valid_settings = Settings(
        app_env="production",
        debug=False,
        secret_key="super-secure-production-secret-key-with-high-entropy-123456",
        database_url="postgresql+psycopg://slotback:pw@localhost/slotback",
        cors_origins="https://slotback.com,https://app.slotback.com",
    )
    valid_settings.validate_production_configuration()  # Should not raise


def test_liveness_and_readiness_checks():
    """Verify separate liveness and database-readiness endpoints."""
    # Liveness check
    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json() == {"status": "ok", "service": "slotback-api"}

    # Readiness check (DB connected)
    ready_res = client.get("/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"
    assert ready_res.json()["database"] == "connected"


def test_bounded_notification_retries(admin_headers):
    """Verify that notification retries are bounded to a maximum of 3 attempts."""
    # Ensure auto_match is false so we can create an offer explicitly with failure simulation
    settings = client.get("/api/v1/settings", headers=admin_headers).json()
    settings["auto_match_waitlist"] = False
    client.put("/api/v1/settings", headers=admin_headers, json=settings)

    # Setup service, waitlist, cancelled appointment, and offer
    svc = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"name": "Retry Test Service", "duration_minutes": 30, "price": 60.0},
    ).json()

    wl = client.post(
        "/api/v1/waitlist",
        json={
            "customer_name": "Retry Customer",
            "customer_email": "retry@example.com",
            "customer_phone": "555-9999",
            "service_id": svc["id"],
            "preferred_start_date": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "preferred_end_date": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
    ).json()

    start_time = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    appt = client.post(
        "/api/v1/appointments",
        json={
            "customer_name": "Orig Customer",
            "customer_email": "orig@example.com",
            "customer_phone": "555-0000",
            "service_id": svc["id"],
            "start_time": start_time,
        },
    ).json()

    client.post(f"/api/v1/appointments/{appt['id']}/cancel", headers=admin_headers, json={})

    offer = client.post(
        "/api/v1/recovery/offers",
        headers=admin_headers,
        json={
            "appointment_id": appt["id"],
            "waitlist_id": wl["id"],
            "simulate_notification_failure": True,
        },
    ).json()

    notif_id = offer["notification_logs"][0]["id"]

    # Retry 1, 2, 3 should succeed
    for _ in range(3):
        res = client.post(f"/api/v1/recovery/notifications/{notif_id}/retry", headers=admin_headers)
        assert res.status_code == 200

    # Retry 4 must be rejected with 400 Bad Request (Maximum retry limit exceeded)
    res_exceeded = client.post(f"/api/v1/recovery/notifications/{notif_id}/retry", headers=admin_headers)
    assert res_exceeded.status_code == 400
    assert "Maximum notification retry limit (3) exceeded" in res_exceeded.json()["detail"]


def test_admin_can_list_staff_users_and_staff_cannot(
    admin_headers: dict[str, str], staff_headers: dict[str, str]
):
    """Admin can list staff members to set up auth, but regular staff cannot."""
    # 1. Staff cannot list users (403)
    res_staff = client.get("/api/v1/auth/users", headers=staff_headers)
    assert res_staff.status_code == 403

    # 2. Admin can list users (200)
    res_admin = client.get("/api/v1/auth/users", headers=admin_headers)
    assert res_admin.status_code == 200
    users = res_admin.json()
    assert isinstance(users, list)
    assert len(users) >= 1
    assert any(u["role"] == "admin" for u in users)
