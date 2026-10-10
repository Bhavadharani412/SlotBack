# SlotBack — Architecture

## Overview

SlotBack is a three-tier web application: a React SPA frontend, a FastAPI backend, and a PostgreSQL database managed by Alembic migrations.

```
┌─────────────────────────────┐
│     Browser (Staff/Customer)│
│  React + TypeScript + Vite  │
│  React Router / plain CSS   │
└──────────────┬──────────────┘
               │ HTTP/JSON (fetch)
               ▼
┌─────────────────────────────┐
│  FastAPI application        │
│  backend/app/main.py        │
│  ├── API Router (/api/v1)   │◄─── OpenAPI docs at /docs
│  ├── CORS Middleware        │
│  └── SPA Static Serving     │ (serves frontend/dist)
└──────────────┬──────────────┘
               │ SQLAlchemy 2.x (psycopg 3)
               ▼
┌─────────────────────────────┐
│  SlotBackService            │
│  backend/app/services/      │
│  recovery_service.py        │
│  (All business logic here)  │
└──────────────┬──────────────┘
               │ ORM / raw SELECT
               ▼
┌─────────────────────────────┐
│  PostgreSQL                 │
│  slotback (dev)             │
│  slotback_test (tests)      │
│  Migrations: Alembic        │
└─────────────────────────────┘
```

---

## Component Responsibilities

### Frontend (`frontend/src/`)

| Component | Responsibility |
|---|---|
| `App.tsx` | Route declarations, `<Navigation>` mounting |
| `components/Navigation.tsx` | Sidebar + topbar; mobile hamburger toggle |
| `pages/OverviewPage.tsx` | Dashboard: metrics, urgent cancellations, active offers |
| `pages/AppointmentsPage.tsx` | Appointment list, create/cancel modals |
| `pages/WaitlistPage.tsx` | Waitlist management |
| `pages/RecoveryPage.tsx` | Released slots, offer issue/withdraw, notification retry |
| `pages/ReportsPage.tsx` | Recovery metrics visualization |
| `pages/SettingsPage.tsx` | Business config, service management |
| `pages/CustomerBookingPage.tsx` | Public booking form |
| `pages/CustomerOfferPage.tsx` | Offer view + accept, expiry countdown |
| `api/client.ts` | All HTTP calls to `/api/v1`; no mock data |
| `index.css` | CSS design system (variables, page-header, table, buttons, responsive) |

**Data policy:** The frontend fetches exclusively from the API. No mock arrays, hardcoded data, or fallback records exist in production code. Empty states are displayed when the database has no records.

### Backend (`backend/app/`)

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI app factory, CORS, lifespan (schema create), SPA serving |
| `core/config.py` | Pydantic `Settings` from environment; `TEST_DATABASE_URL` safety field |
| `api/v1/endpoints.py` | Thin FastAPI router — delegates all logic to `SlotBackService` |
| `services/recovery_service.py` | All domain logic: appointments, waitlist, offers, metrics, settings |
| `models/domain.py` | SQLAlchemy ORM models: Service, Appointment, WaitlistEntry, RecoveryOffer, NotificationLog, BusinessSetting |
| `schemas/domain.py` | Pydantic v2 request/response schemas |
| `db/session.py` | Engine + SessionLocal + `get_db` dependency |

### Database (PostgreSQL)

| Table | Key columns |
|---|---|
| `services` | id, name, duration_minutes, price, is_active |
| `appointments` | id, customer_*, service_id, start_time, end_time, status, cancelled_at, is_recovery |
| `waitlist_entries` | id, customer_*, service_id, preferred_start_date, preferred_end_date, status |
| `recovery_offers` | id, appointment_id, waitlist_id, token (UUID), status, expires_at, accepted_at |
| `notification_logs` | id, offer_id, recipient_email, channel, status, retry_count, error_message |
| `business_settings` | id=1 (singleton), auto_match_waitlist, default_offer_expiry_minutes |

---

## API / Data Flow

### Cancellation → Recovery

```
POST /api/v1/appointments/{id}/cancel
  → SlotBackService.cancel_appointment()
      → sets appointment.status = "cancelled"
      → if settings.auto_match_waitlist:
          → get_eligible_waitlist_for_appointment()
          → create_recovery_offer() (with notification log)
  → returns cancelled Appointment
```

### Offer Acceptance (atomic)

```
POST /api/v1/recovery/offers/{token}/accept
  → SlotBackService.accept_offer()
      → SELECT RecoveryOffer WHERE token=? FOR UPDATE
      → SELECT Appointment WHERE id=? FOR UPDATE
      → Validate: status not "accepted"/"expired"/"withdrawn"
      → Validate: expires_at > now()
      → Update appointment: customer=waitlist_entry, status="scheduled", is_recovery=True
      → Update offer: status="accepted", accepted_at=now()
      → Update waitlist_entry: status="fulfilled"
      → COMMIT (atomic)
  → returns {status: "confirmed", appointment, offer}
```

---

## Domain Rules

1. **One offer per slot**: A `cancelled` appointment can have at most one non-expired, non-withdrawn active offer at a time.
2. **Eligibility**: A waitlist entry matches an appointment if: `service_id` matches, `status = "active"`, and `preferred_start_date ≤ appointment.start_time ≤ preferred_end_date`.
3. **FIFO matching**: When multiple eligible entries exist, the one with the earliest `created_at` is chosen.
4. **Expiry enforcement**: Offers past `expires_at` are rejected at acceptance time (and lazily marked expired on list reads).
5. **Idempotent cancellation**: Cancelling an already-cancelled appointment is a no-op (returns the existing record).

---

## Transaction & Concurrency

The acceptance path uses `SELECT … FOR UPDATE` row-level locks on both the `recovery_offers` and `appointments` rows within a single transaction. This prevents two concurrent customers from both accepting the same offer — exactly one transaction will commit, the other will see `status = "accepted"` and receive a 400.

**Note:** Email notification delivery is **simulated**. No SMTP or provider calls are made. The `NotificationLog.status` field is set to `"delivered"` or `"failed"` based on the `simulate_notification_failure` flag for staff testing purposes only.

---

## Security Constraints (Current State)

- **No authentication**: All `/api/v1` endpoints are publicly accessible. This is a **release blocker**.
- **CORS**: Configurable via `CORS_ORIGINS`. Set to exact domain in production. The fallback `["*"]` is only acceptable in development.
- **Input validation**: Pydantic v2 schemas enforce all inputs on the backend.
- **No raw SQL**: All queries use SQLAlchemy ORM or `select()` expressions; no string interpolation.
- **No secrets in code**: All configuration via environment variables.
