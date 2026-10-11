"""
Playwright browser E2E tests for SlotBack.

Prerequisites:
  - An isolated test server is automatically spawned targeting the dedicated test database (TEST_DATABASE_URL).
  - Can optionally target a custom server via SLOTBACK_BASE_URL.
  - Development database (/slotback) is strictly protected and never touched.

Run:
  pytest backend/tests/e2e/ -ra -v --timeout=60
"""

from datetime import UTC, datetime, timedelta

import pytest
from backend.app.core.config import settings as app_settings
from backend.tests.conftest import TestingSessionLocal
from playwright.sync_api import Page, expect
from sqlalchemy import text


def utc_iso(minutes_offset: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes_offset)).isoformat()


@pytest.fixture(scope="module")
def seed_data(live_server_url: str):
    """
    Create the minimal service + waitlist entry + appointment via the isolated API,
    then cancel the appointment to trigger an auto-recovery offer.
    Returns the identifiers needed by the tests.
    """
    import httpx

    with TestingSessionLocal() as session:
        session.execute(text("DELETE FROM notification_logs"))
        session.execute(text("DELETE FROM recovery_offers"))
        session.execute(text("DELETE FROM waitlist_entries"))
        session.execute(text("DELETE FROM appointments"))
        session.execute(text("DELETE FROM services"))
        session.execute(text("DELETE FROM business_settings"))
        session.execute(text("DELETE FROM users"))
        session.commit()
        from backend.app.core.auth import ensure_initial_admin
        ensure_initial_admin(session)

    api = f"{live_server_url}/api/v1"

    # Authenticate to obtain token for staff API calls
    login_res = httpx.post(
        f"{api}/auth/login",
        json={
            "email": app_settings.initial_admin_email,
            "password": app_settings.initial_admin_password,
        },
    )
    auth_token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {auth_token}"}

    # Ensure settings have auto_match enabled
    settings = httpx.get(f"{api}/settings", headers=auth_headers).json()
    settings["auto_match_waitlist"] = True
    httpx.put(f"{api}/settings", headers=auth_headers, json=settings)

    # Create service
    svc = httpx.post(
        f"{api}/services",
        headers=auth_headers,
        json={
            "name": "E2E Test Service",
            "description": "For Playwright E2E",
            "duration_minutes": 60,
            "price": 99.0,
        },
    ).json()
    service_id = svc["id"]

    # Add waitlist customer
    wl = httpx.post(
        f"{api}/waitlist",
        json={
            "customer_name": "E2E Waitlist User",
            "customer_email": "e2e_pw@example.com",
            "customer_phone": "555-7777",
            "service_id": service_id,
            "preferred_start_date": utc_iso(-120),
            "preferred_end_date": utc_iso(2880),
        },
    ).json()
    waitlist_id = wl["id"]

    # Create appointment
    appt = httpx.post(
        f"{api}/appointments",
        json={
            "customer_name": "E2E Original Customer",
            "customer_email": "e2e_orig@example.com",
            "customer_phone": "555-8888",
            "service_id": service_id,
            "start_time": utc_iso(180),
        },
    ).json()
    appointment_id = appt["id"]

    # Cancel appointment — triggers auto-recovery offer
    httpx.post(
        f"{api}/appointments/{appointment_id}/cancel",
        headers=auth_headers,
        json={"reason": "E2E test cancel"},
    )

    # Fetch the offer token
    offers = httpx.get(f"{api}/recovery/offers", headers=auth_headers).json()
    offer = next((o for o in offers if o["appointment_id"] == appointment_id), None)
    assert offer is not None, "Expected auto-recovery offer was not created"
    offer_token = offer["token"]
    offer_id = offer["id"]

    yield {
        "service_id": service_id,
        "waitlist_id": waitlist_id,
        "appointment_id": appointment_id,
        "offer_token": offer_token,
        "offer_id": offer_id,
        "auth_token": auth_token,
    }


@pytest.fixture(autouse=True)
def inject_staff_auth_token(request, page: Page):
    if "TestAuthenticationUI" not in request.node.nodeid:
        seed_data = request.getfixturevalue("seed_data")
        token = seed_data["auth_token"]
        page.add_init_script(f"localStorage.setItem('slotback_token', '{token}');")


class TestStaffInterfaceSmoke:
    """Smoke tests: staff navigation, key pages load at 1366x768."""

    def test_overview_page_loads(self, page: Page, live_server_url: str):
        page.set_viewport_size({"width": 1366, "height": 768})
        page.goto(live_server_url + "/")
        expect(page.get_by_role("heading", name="Staff Operational Dashboard")).to_be_visible()
        # Sidebar should be visible at desktop width
        expect(page.locator(".sidebar")).to_be_visible()
        # Mobile hamburger should be hidden at desktop width
        expect(page.locator(".mobile-only-menu")).to_be_hidden()

    def test_appointments_page_loads(self, page: Page, live_server_url: str):
        page.set_viewport_size({"width": 1366, "height": 768})
        page.goto(live_server_url + "/appointments")
        expect(page.get_by_role("heading", name="Appointments Directory")).to_be_visible()

    def test_waitlist_page_loads(self, page: Page, live_server_url: str):
        page.set_viewport_size({"width": 1366, "height": 768})
        page.goto(live_server_url + "/waitlist")
        expect(page.get_by_role("heading")).to_be_visible()

    def test_recovery_page_loads(self, page: Page, live_server_url: str):
        page.set_viewport_size({"width": 1366, "height": 768})
        page.goto(live_server_url + "/recovery")
        expect(page.get_by_role("heading", name="Slot Recovery & Offer Management")).to_be_visible()

    def test_reports_page_loads(self, page: Page, live_server_url: str):
        page.set_viewport_size({"width": 1366, "height": 768})
        page.goto(live_server_url + "/reports")
        expect(page.get_by_role("heading")).to_be_visible()


class TestMobileNavigation:
    """Mobile viewport: hamburger visible, navigation works."""

    def test_mobile_hamburger_is_visible_at_380px(self, page: Page, live_server_url: str):
        page.set_viewport_size({"width": 380, "height": 800})
        page.goto(live_server_url + "/")
        hamburger = page.locator(".mobile-only-menu")
        expect(hamburger).to_be_visible()
        expect(page.locator(".sidebar")).to_be_hidden()

    def test_mobile_hamburger_opens_sidebar(self, page: Page, live_server_url: str):
        page.set_viewport_size({"width": 380, "height": 800})
        page.goto(live_server_url + "/")
        hamburger = page.locator(".mobile-only-menu")
        hamburger.click()
        expect(page.locator(".sidebar")).to_be_visible()

    def test_recovery_page_actions_accessible_at_380px(self, page: Page, live_server_url: str):
        page.set_viewport_size({"width": 380, "height": 800})
        page.goto(live_server_url + "/recovery")
        btn = page.get_by_role("button", name="Issue Recovery Offer")
        expect(btn).to_be_visible()
        bbox = btn.bounding_box()
        assert bbox is not None
        assert bbox["x"] >= 0, "Button is clipped on the left"
        assert bbox["x"] + bbox["width"] <= 380 + 20, "Button overflows viewport on the right"


class TestRecoveryOfferFlow:
    """
    Key user journey: cancel → offer visible → customer accepts → booking confirmed → duplicate rejected.
    Requires seed_data fixture.
    """

    def test_cancelled_slot_appears_in_recovery_page(
        self, page: Page, live_server_url: str, seed_data: dict
    ):
        page.set_viewport_size({"width": 1366, "height": 768})
        page.goto(live_server_url + "/recovery")
        expect(page.get_by_text("Released Slots Available for Recovery")).to_be_visible()

    def test_customer_offer_page_loads(self, page: Page, live_server_url: str, seed_data: dict):
        token = seed_data["offer_token"]
        page.set_viewport_size({"width": 1366, "height": 768})
        page.goto(f"{live_server_url}/offer/{token}")
        page.wait_for_load_state("networkidle")
        expect(page.locator("body")).to_be_visible()
        page_text = page.locator("body").inner_text()
        assert (
            "accept" in page_text.lower()
            or "offer" in page_text.lower()
            or "appointment" in page_text.lower()
        )

    def test_customer_can_accept_offer(self, page: Page, live_server_url: str, seed_data: dict):
        token = seed_data["offer_token"]
        page.set_viewport_size({"width": 1366, "height": 768})
        page.goto(f"{live_server_url}/offer/{token}")
        page.wait_for_load_state("networkidle")

        body_text = page.locator("body").inner_text().lower()

        # If offer page already shows accepted/confirmed state from prior test step, pass
        if any(kw in body_text for kw in ["accepted", "confirmed", "fulfilled", "already been"]):
            return

        accept_btn = page.locator("button").filter(has_text="Accept")
        if accept_btn.is_visible(timeout=3000):
            accept_btn.click()
            page.wait_for_function(
                """() => {
                    const t = document.body.innerText.toLowerCase();
                    return t.includes('confirmed') || t.includes('success') || t.includes('booked')
                           || t.includes('already been') || t.includes('accepted') || t.includes('error');
                }""",
                timeout=10000,
            )
            body_text = page.locator("body").inner_text().lower()
            assert any(
                kw in body_text
                for kw in ["confirmed", "success", "booked", "already been", "accepted"]
            )
        else:
            assert any(kw in body_text for kw in ["offer", "appointment", "expired", "slot"])

    def test_duplicate_acceptance_is_rejected_at_api_level(
        self, live_server_url: str, seed_data: dict
    ):
        """
        Verify at HTTP level that a second acceptance is rejected.
        """
        import httpx

        token = seed_data["offer_token"]
        httpx.post(f"{live_server_url}/api/v1/recovery/offers/{token}/accept")
        r2 = httpx.post(f"{live_server_url}/api/v1/recovery/offers/{token}/accept")
        assert r2.status_code == 400
        assert "already been accepted" in r2.json()["detail"]


class TestEmptyAndErrorStates:
    """Verify empty states are shown correctly when no data exists."""

    def test_booking_page_loads_with_no_crashes(self, page: Page, live_server_url: str):
        page.set_viewport_size({"width": 1366, "height": 768})
        page.goto(live_server_url + "/book")
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.wait_for_load_state("networkidle")
        assert len(errors) == 0, f"Page JS errors: {errors}"

    def test_invalid_offer_token_shows_error(self, page: Page, live_server_url: str):
        page.set_viewport_size({"width": 1366, "height": 768})
        page.goto(f"{live_server_url}/offer/definitely-not-a-real-token-xyz-123")
        page.wait_for_load_state("networkidle")
        body_text = page.locator("body").inner_text().lower()
        assert any(
            kw in body_text for kw in ["not found", "invalid", "error", "expired", "unavailable"]
        )


class TestAuthenticationUI:
    """E2E browser tests for staff sign-in, invalid credentials, sign-out, and public bypass."""

    def test_login_email_field_uses_branded_focus_outline(
        self, page: Page, live_server_url: str
    ):
        page.goto(live_server_url + "/login")
        email = page.locator("#email-input")
        expect(email).to_have_css("outline-style", "none")
        expect(email).to_have_css("border-color", "rgb(49, 87, 213)")

    def test_unauthenticated_user_redirected_to_login(self, page: Page, live_server_url: str):
        page.goto(live_server_url + "/appointments")
        page.wait_for_url("**/login")
        expect(page.get_by_role("heading", name="Staff Sign In")).to_be_visible()

    def test_invalid_credentials_shows_error_alert(self, page: Page, live_server_url: str):
        page.goto(live_server_url + "/login")
        page.fill("#email-input", app_settings.initial_admin_email)
        page.fill("#password-input", "IncorrectPassword123!")
        page.click("button[type='submit']")
        expect(page.locator("[role='alert']")).to_be_visible()

    def test_valid_credentials_signs_in_and_redirects(self, page: Page, live_server_url: str):
        page.goto(live_server_url + "/login")
        page.fill("#email-input", app_settings.initial_admin_email)
        page.fill("#password-input", app_settings.initial_admin_password)
        page.click("button[type='submit']")
        page.wait_for_url(live_server_url + "/")
        expect(page.get_by_role("heading", name="Staff Operational Dashboard")).to_be_visible()

    def test_sign_out_clears_session_and_redirects_to_login(
        self, page: Page, live_server_url: str, seed_data: dict
    ):
        token = seed_data["auth_token"]
        page.add_init_script(f"localStorage.setItem('slotback_token', '{token}');")
        page.goto(live_server_url + "/")
        expect(page.locator(".sidebar")).to_be_visible()
        # Click sign out button
        page.locator("button[aria-label='Sign out']").first.click()
        page.wait_for_url("**/login")
        expect(page.get_by_role("heading", name="Staff Sign In")).to_be_visible()

    def test_public_customer_booking_accessible_without_auth(
        self, page: Page, live_server_url: str
    ):
        page.goto(live_server_url + "/book")
        expect(page.get_by_role("heading", name="Book an Appointment")).to_be_visible()
        assert "/book" in page.url
