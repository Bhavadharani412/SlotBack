# SlotBack — Testing Guide

## Test Categories

SlotBack has three distinct test categories. They run against different environments and verify different layers.

| Category | Location | Database | CI Job |
|---|---|---|---|
| **Unit** | `backend/tests/unit/` | None (mocked) | `backend` |
| **Integration/API** | `backend/tests/api/` | `slotback_test` (PostgreSQL) | `backend` |
| **Browser E2E** | `backend/tests/e2e/` | `slotback_test` or `slotback_e2e` (PostgreSQL) | `e2e` |

---

## Test Database Isolation & Ephemeral Server

**Safety guarantee:** Tests cannot accidentally modify or pollute the development database (`slotback`).

1. **Safety Enforcer:** `backend/tests/conftest.py` inspects the resolved test database URL. If it resolves to `/slotback` (the dev database), it **raises a `RuntimeError`**, failing the test immediately.
2. **FastAPI Dependency Override:** `conftest.py` creates `test_engine` and `TestingSessionLocal` connected exclusively to the test database and overrides FastAPI's `get_db` dependency.
3. **Dedicated Ephemeral E2E Server:** `backend/tests/e2e/conftest.py` dynamically spins up an ephemeral `uvicorn.Server` on a free port (`127.0.0.1:<port>`) with the test database dependency override and static SPA serving. E2E browser tests automatically connect to this isolated server.
4. **Zero Dev DB Pollution:** Running `pytest backend/tests/e2e/` runs completely isolated against `slotback_test` / `slotback_e2e`, leaving any running development server and database untouched.

### Setting up the test database locally

```powershell
# Creates slotback_test database and grants privileges to the slotback role
python scripts/setup_postgres.py
```

Ensure `.env` has:
```ini
TEST_DATABASE_URL=postgresql+psycopg://slotback:slotback_dev_password@localhost:5432/slotback_test
```

---

## Running Tests

### Unit tests (no database required)

```powershell
pytest backend/tests/unit/ -ra -v
```

These tests mock the SQLAlchemy session and verify pure business logic. Safe to run at any time.

### Integration/API tests (requires `slotback_test`)

```powershell
pytest backend/tests/api/ -ra -v
```

### Browser E2E tests (Playwright)

```powershell
# Spawns isolated ephemeral test server and runs Playwright chromium tests
pytest backend/tests/e2e/ -ra -v
```

Optionally set `SLOTBACK_BASE_URL` to point to a custom staging or CI environment URL.

### Frontend TypeScript check

```powershell
pnpm --prefix frontend exec tsc --noEmit
```

### Frontend build

```powershell
pnpm --prefix frontend build
```

---

## Coverage by Critical Workflow

### Unit tests (`backend/tests/unit/test_business_rules.py` & `test_health.py`) — 19 Tests

| Business rule | Test |
|---|---|
| Eligible waitlist entry matches service + date window | `test_eligible_entry_matches_service_and_date_window` |
| Empty waitlist returns empty list | `test_empty_result_when_no_waitlist_entries` |
| Auto-issue returns None when no eligible customers | `test_auto_issue_returns_none_when_no_eligible_customers` |
| Expired offer rejected on accept | `test_accept_offer_rejects_if_expired` |
| Future offer is valid | `test_offer_future_expiry_is_valid` |
| Past expiry offer is expired | `test_offer_past_expiry_is_expired` |
| Already-accepted offer rejected | `test_accept_offer_rejects_already_accepted` |
| Withdrawn offer rejected | `test_accept_offer_rejects_withdrawn` |
| Cancelling already-cancelled appointment is idempotent | `test_cancel_appointment_with_wrong_status_returns_early` |
| Create offer fails if appointment not cancelled | `test_create_offer_rejects_if_appointment_not_cancelled` |
| Create offer fails if waitlist entry fulfilled | `test_create_offer_rejects_if_waitlist_entry_not_eligible` |
| Create offer fails if service mismatch | `test_create_offer_rejects_service_mismatch` |
| Create offer fails if outside date window | `test_create_offer_rejects_outside_date_window` |
| Withdrawing accepted offer is rejected | `test_withdraw_accepted_offer_raises_error` |
| Recovery rate = 0 when no cancellations | `test_recovery_rate_is_zero_when_no_cancellations` |
| Recovery rate = 100% when all recovered | `test_recovery_rate_100_when_all_cancellations_recovered` |
| Notification failure rate formula | `test_notification_failure_rate_calculated_correctly` |
| Median time is None with no accepted offers | `test_median_time_is_none_when_no_accepted_offers` |
| Health check endpoint reports status | `test_health_endpoint_reports_service_status` |

### Integration/API tests (`backend/tests/api/`) — 6 Tests

| Scenario | Test |
|---|---|
| Full cancellation → auto-match → offer → acceptance → metrics | `test_full_cancellation_to_recovery_workflow` |
| Duplicate acceptance rejected (400) | `test_full_cancellation_to_recovery_workflow` |
| Notification failure simulation + retry | `test_notification_failure_and_retry` |
| Ineligible waitlist customer rejected on manipulated direct request (service mismatch & date mismatch) | `test_ineligible_waitlist_customer_rejected_even_if_manipulated_request` |
| Timezone-aware date matching and booking with offsets (+05:30, Z) | `test_timezone_aware_date_matching_and_booking` |
| Overlapping appointment booking conflict returns 409 Conflict | `test_overlapping_booking_conflict_prevention` |
| 8-step critical path (create, cancel, offer, accept, dup-reject, metrics, conflict, fail+retry) | `test_complete_8_step_critical_e2e_workflow` |

### Browser E2E tests (`backend/tests/e2e/`) — 14 Tests

| Scenario | Test |
|---|---|
| Staff portal pages load at 1366×768 | `TestStaffInterfaceSmoke` (5 tests) |
| Mobile hamburger visible at 380×800 | `test_mobile_hamburger_is_visible_at_380px` |
| Mobile hamburger opens sidebar | `test_mobile_hamburger_opens_sidebar` |
| Issue Recovery Offer button accessible at 380×800 | `test_recovery_page_actions_accessible_at_380px` |
| Released slot visible in recovery page | `test_cancelled_slot_appears_in_recovery_page` |
| Customer offer page loads | `test_customer_offer_page_loads` |
| Customer can accept offer | `test_customer_can_accept_offer` |
| Duplicate acceptance rejected (HTTP + browser) | `test_duplicate_acceptance_is_rejected_at_api_level` |
| Booking page loads without JS errors | `test_booking_page_loads_with_no_crashes` |
| Invalid token shows error state | `test_invalid_offer_token_shows_error` |

---

## Actual Verification Summary (Real Test Runs)

| Suite / Command | Exact Command | Real Result | Exit Code | Duration |
|---|---|---|---|---|
| **Unit Tests** | `pytest backend/tests/unit/ -ra -v` | **19/19 PASSED** | `0` | 0.61s |
| **API Integration Tests** | `pytest backend/tests/api/ -ra -v` | **6/6 PASSED** | `0` | 1.97s |
| **Browser E2E Tests** | `pytest backend/tests/e2e/ -ra -v` | **14/14 PASSED** | `0` | 23.93s |
| **Python Linting** | `ruff check .` | **All checks passed** | `0` | 0.15s |
| **TypeScript Check** | `pnpm --prefix frontend exec tsc --noEmit` | **0 errors** | `0` | 1.8s |
| **Frontend Production Build** | `pnpm --prefix frontend build` | **Built 242.97 kB bundle** | `0` | 6.47s |

---

## Known Gaps & Release Blockers

- **Release Blocker — Missing Staff Authentication & Authorization**: Staff endpoints (`/api/v1/appointments`, `/api/v1/services`, `/api/v1/settings`, `/api/v1/recovery/offers` creation/withdrawal) have no authentication. SlotBack must not be deployed to public production until staff authentication and RBAC are implemented.
- **Notification SMTP Integration**: Notification delivery and retry are simulated through database status transitions and mock logs; real third-party SMTP/SMS providers are not yet wired up.
