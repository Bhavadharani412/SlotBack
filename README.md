# SlotBack

> **Appointment cancellation-recovery for small service businesses.**
>
> When a booking is cancelled, SlotBack automatically matches the freed slot to the most eligible waitlisted customer, sends them a time-limited acceptance offer, and confirms exactly one replacement booking — preventing lost revenue from no-shows and cancellations.

---

## Table of Contents

- [Problem & Value Proposition](#problem--value-proposition)
- [Target Users](#target-users)
- [Implemented Features vs Simulated / Incomplete](#implemented-features-vs-simulated--incomplete)
- [Screens & Their Purpose](#screens--their-purpose)
- [Full Recovery Flow](#full-recovery-flow)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Prerequisites & Setup](#prerequisites--setup)
- [Running Locally](#running-locally)
- [Testing](#testing)
- [Demo Data Policy](#demo-data-policy)
- [Security Limitations & Known Issues](#security-limitations--known-issues)
- [Deployment Status](#deployment-status)
- [Configuration Reference](#configuration-reference)
- [Detailed Documentation](#detailed-documentation)

---

## Problem & Value Proposition

Small service businesses (salons, physio clinics, massage studios) lose revenue every time an appointment is cancelled. A waitlisted customer who would have taken that slot often goes uncontacted.

SlotBack provides a lightweight staff portal where:
- Released slots are automatically matched to eligible waitlist customers.
- A unique, expiring acceptance link is issued per match.
- The first customer to accept gets the booking; duplicate acceptances are rejected.
- Staff can monitor offer states, retry failed notifications, and view recovery metrics.

---

## Target Users

| Role | Interface |
|---|---|
| **Staff** | `/` (staff portal, all pages except `/book` and `/offer/:token`) |
| **Customer (booking)** | `/book` — browse services and book an appointment |
| **Customer (offer)** | `/offer/:token` — view and accept a recovery offer |

---

## Implemented Features vs Simulated / Incomplete

### ✅ Implemented and working
- Appointment creation with conflict detection (409 for overlapping bookings)
- Appointment cancellation with reason recording
- Waitlist management (add, cancel, filter entries)
- Auto-matching: on cancellation, the oldest eligible waitlist entry receives an offer
- Manual offer issuance from the Slot Recovery page
- Offer acceptance with row-level locking (`SELECT … FOR UPDATE`) — only one acceptance confirmed
- Duplicate acceptance rejection (400 with clear message)
- Offer expiry enforcement — offers past their deadline cannot be accepted
- Offer withdrawal by staff
- Notification logging per offer (simulated delivery — see below)
- Notification retry endpoint
- Recovery metrics (cancellations, recoveries, rate, median time to refill, notification failure rate)
- Staff portal (Overview, Appointments, Waitlist, Slot Recovery, Reports, Settings)
- Customer booking page (`/book`)
- Customer offer page (`/offer/:token`)
- PostgreSQL integration with Alembic migrations
- Isolated test database (`slotback_test`) with safety guard against dev DB contamination
- GitHub Actions CI (backend linting, migration validation, tests; frontend TypeScript check and build)

### ⚠️ Simulated / Not production-ready
- **Notification delivery is simulated** — no real SMTP or messaging provider is integrated. The `simulate_notification_failure` toggle is a staff testing aid. Notification logs record "delivered" without any real email being sent.
- **No staff authentication or authorization** — all staff endpoints are publicly accessible. This is a **release blocker** before production deployment.
- **No production deployment** — the app is not deployed to any public URL. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the deployment plan.

---

## Screens & Their Purpose

| Screen | URL | Purpose |
|---|---|---|
| **Overview** | `/` | Workload snapshot: urgent cancellations, active offers, notification failures, key metrics |
| **Appointments** | `/appointments` | Full appointment list with search, filter by status/service, book new, cancel |
| **Waitlist** | `/waitlist` | Add/remove waitlisted customers, view eligibility windows |
| **Slot Recovery** | `/recovery` | Released slots awaiting offers, issue/withdraw offers, retry notifications, offer state table |
| **Reports** | `/reports` | Recovery rate, median time to refill, notification failure rate — computed from DB |
| **Settings** | `/settings` | Business settings, default offer expiry, auto-match toggle, service management |
| **Customer Booking** | `/book` | Public booking page: browse services, submit appointment request |
| **Customer Offer** | `/offer/:token` | Accept or view a recovery offer; shows expiry countdown; duplicate acceptance is rejected |

---

## Full Recovery Flow

```
[Staff/Customer] books appointment → Appointment created (status: scheduled)
       ↓
[Staff] cancels appointment → status: cancelled, cancellation_reason + cancelled_at recorded
       ↓
[Auto-match] OR [Staff Manual Match]
  → Oldest active waitlist entry for same service + overlapping preferred window selected
  → RecoveryOffer created (status: sent, unique token, expiry timestamp)
  → NotificationLog recorded (simulated: "delivered" or "failed" if simulate_notification_failure)
       ↓
[Customer] opens /offer/<token>
  → Expiry checked; expired offers return 400
       ↓
[Customer] clicks Accept
  → SELECT … FOR UPDATE on offer + appointment rows
  → Status and expiry re-validated atomically
  → appointment.customer_name/email/phone updated to waitlist customer
  → appointment.status = "scheduled", appointment.is_recovery = True
  → offer.status = "accepted", waitlist_entry.status = "fulfilled"
  → All committed in one transaction
       ↓
[Second acceptance attempt] → 400 "already been accepted"
       ↓
[Reports] eligible_cancellations, recovered_appointments, recovery_rate computed from DB
```

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full component diagram and concurrency details.

**Summary:**

```
React (Vite) ──── HTTP/JSON ──── FastAPI (/api/v1) ──── SlotBackService ──── SQLAlchemy 2.x ──── PostgreSQL
                                     │
                                  Alembic (migrations)
```

- **Frontend** (`frontend/src/`): React + TypeScript + Vite, plain CSS (`index.css`), React Router. Fetches all data from the API — no mock arrays or hardcoded records in production code.
- **Backend** (`backend/app/`): FastAPI routers (thin), `SlotBackService` (all business logic), SQLAlchemy models, Alembic migrations.
- **Database**: PostgreSQL. `slotback` for development, `slotback_test` for tests.

---

## Repository Structure

```
SlotBack/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints.py      # Thin FastAPI router
│   │   ├── core/config.py           # Settings from env vars
│   │   ├── db/session.py            # SQLAlchemy engine + Base
│   │   ├── models/domain.py         # ORM models
│   │   ├── schemas/domain.py        # Pydantic v2 schemas
│   │   ├── services/recovery_service.py  # All business logic
│   │   └── main.py                  # App factory, CORS, SPA serving
│   └── tests/
│       ├── conftest.py              # Isolated test DB setup + safety guard
│       ├── unit/                    # Pure business rule tests (no DB)
│       │   └── test_business_rules.py
│       ├── api/                     # HTTP integration tests (PostgreSQL)
│       │   ├── test_recovery_flow.py
│       │   └── test_e2e_critical_path.py
│       └── e2e/                     # Playwright browser tests
│           └── test_browser_recovery_flow.py
├── frontend/
│   ├── src/
│   │   ├── pages/                   # OverviewPage, AppointmentsPage, etc.
│   │   ├── components/              # Navigation, Modal, StatusBadge, etc.
│   │   ├── api/client.ts            # API client
│   │   └── index.css                # Design system (CSS variables + utilities)
│   ├── package.json
│   └── pnpm-lock.yaml
├── migrations/                      # Alembic migration scripts
├── scripts/setup_postgres.py        # Local DB provisioning (dev only)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── TESTING.md
│   ├── METRICS.md
│   ├── DEPLOYMENT.md
│   └── PROJECT_OVERVIEW.md
├── .github/workflows/ci.yml         # GitHub Actions CI
├── .env.example                     # Env var template (no real secrets)
├── alembic.ini
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

---

## Prerequisites & Setup

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12+ | Required |
| PostgreSQL | 14+ | Running locally or via Docker |
| Node.js | 20+ | For frontend build |
| pnpm | 9+ | Package manager (use `npm i -g pnpm` or `npx pnpm`) |

**1. Environment variables**

```powershell
copy .env.example .env
```

Edit `.env` with your local values. **Never commit `.env`.**

```ini
# .env.example (no real secrets — safe to commit)
APP_NAME=SlotBack
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+psycopg://slotback:slotback_dev_password@localhost:5432/slotback
TEST_DATABASE_URL=postgresql+psycopg://slotback:slotback_dev_password@localhost:5432/slotback_test
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```

**2. Database provisioning (first time only)**

```powershell
# Requires postgres superuser access — dev only
python scripts/setup_postgres.py
```

This creates the `slotback` role (non-superuser), `slotback` database, and `slotback_test` database.

**3. Python virtual environment**

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt
```

---

## Running Locally

**Backend (API + serves built frontend):**

```powershell
alembic upgrade head
.venv\Scripts\uvicorn backend.app.main:app --reload --port 8000
```

Open:
- `http://localhost:8000` — Staff portal
- `http://localhost:8000/book` — Customer booking page
- `http://localhost:8000/docs` — OpenAPI interactive docs

**Frontend dev server (hot-reload):**

```powershell
pnpm --prefix frontend install --frozen-lockfile
pnpm --prefix frontend dev
```

Opens at `http://localhost:5173` (proxies `/api` to port 8000).

**Build frontend for production:**

```powershell
pnpm --prefix frontend build
```

---

## Testing

See [docs/TESTING.md](docs/TESTING.md) for full test category descriptions, isolation guarantees, and actual results.

### Backend unit tests (no database)

```powershell
pytest backend/tests/unit/ -ra -v
```

17 tests covering: waitlist eligibility, offer expiration, status transitions, metric calculations, empty cases.

### Backend integration/API tests (requires PostgreSQL `slotback_test`)

```powershell
# Set TEST_DATABASE_URL in .env (must not point to slotback dev database)
pytest backend/tests/api/ -ra -v
```

3 tests covering: full cancellation→recovery→acceptance flow, duplicate rejection, notification failure and retry.

### Full backend suite

```powershell
pytest -ra -v
```

**Verified result: 34/34 passed** (19 unit + 15 API & security integration).

### Frontend TypeScript check and build

```powershell
pnpm --prefix frontend exec tsc --noEmit
pnpm --prefix frontend build
```

Both pass with 0 errors, generating the production bundle in `frontend/dist`.

### Browser E2E tests (Playwright)

```powershell
pytest backend/tests/e2e/ -ra -v --timeout=60
```

**Verified result: 14/14 passed** in headless Chromium. Isolated ephemeral test server runs against dedicated test database with automatic staff authentication injection.

### CI Gates

GitHub Actions workflow: `.github/workflows/ci.yml`
- **backend job**: PostgreSQL service, ruff lint, Alembic full migration validation, pytest
- **frontend job**: pnpm frozen install, tsc type check, vite production build
- **e2e job**: Playwright chromium tests running against ephemeral server and clean database

---

## Demo Data Policy

- **No seed script** — the app does not populate demo data automatically.
- **No mock arrays in frontend** — all pages fetch from the API. An empty database renders empty states, not fake data.
- **Test fixtures** (in `conftest.py` and individual test files) create records in `slotback_test`, not the development database. The safety guard in `conftest.py` raises `RuntimeError` if tests would run against `slotback`.
- **Notification delivery**: Supports live SMTP delivery when credentials (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`) are configured. When not configured, structured console notifications are logged with bounded retry tracking (max 3 retries) and never misrepresented as live deliveries.

---

## Security Implementation & Verified Controls

| Domain | Implemented Controls | Status |
|---|---|---|
| **Staff Authentication** | JWT Bearer tokens with HMAC-SHA256, PBKDF2-HMAC-SHA256 password hashing (600,000 rounds) | ✅ Verified (401 on anonymous) |
| **Server-Side RBAC** | Distinct `admin` and `staff` roles; admin required for services, settings, and user creation | ✅ Verified (403 for non-admin) |
| **Capability Token URLs** | Unguessable UUIDv4 tokens for `/offer/:token` customer flows | ✅ Verified |
| **Public Flow Rate Limiting** | In-memory sliding-window rate limiter on login (10/min), booking (30/min), and acceptance (20/min) | ✅ Verified (429 Too Many Requests) |
| **Concurrency Protection** | `SELECT ... FOR UPDATE` row locking during offer acceptance; duplicate acceptance rejected | ✅ Verified |
| **Production Guards** | `Settings.validate_production_configuration()` prevents startup if `DEBUG=true`, `SECRET_KEY` default, or wildcard CORS | ✅ Verified |
| **Health & Readiness** | `/health/live` (process availability) and `/health/ready` (active PostgreSQL ping) | ✅ Verified |

---

## Deployment Status

- **Private Staging Readiness**: Ready for deployment to a private/internal staging environment.
- **Public Beta Readiness**: Ready for limited public beta once a production reverse proxy (TLS/HTTPS termination) and live SMTP credentials are attached.

---

## Configuration Reference

All configuration is through environment variables (no config files with secrets):

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string (`postgresql+psycopg://...`) |
| `TEST_DATABASE_URL` | Tests | Separate test DB; safety guard prevents using main DB |
| `APP_NAME` | | Defaults to `SlotBack API` |
| `APP_ENV` | | `development` / `test` / `production` |
| `DEBUG` | | `true` in development, must be `false` in production |
| `SECRET_KEY` | Production | Min 32-character high-entropy secret for signing JWTs |
| `API_V1_PREFIX` | | Defaults to `/api/v1` |
| `CORS_ORIGINS` | | Comma-separated origins; explicit domain in production |
| `LOG_LEVEL` | | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `SMTP_HOST` | Outbound Mail | SMTP hostname for customer offer notifications |
| `SMTP_PORT` | Outbound Mail | Port (587 TLS or 465 SSL) |
| `SMTP_USER` | Outbound Mail | SMTP username |
| `SMTP_PASSWORD`| Outbound Mail | SMTP password |
| `SMTP_FROM` | Outbound Mail | Sender email address |

---

## Detailed Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Component diagram, API flow, domain rules, concurrency
- [docs/TESTING.md](docs/TESTING.md) — Test categories, isolation, commands, coverage, results, known gaps
- [docs/METRICS.md](docs/METRICS.md) — Metric definitions, formulas, source tables, limitations
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Prerequisites, env vars, DB provisioning, steps, rollback
- [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) — Product scope and roadmap
