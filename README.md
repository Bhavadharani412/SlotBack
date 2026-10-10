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

**Last run result: 20/20 passed** (17 unit + 3 API integration).

### Frontend TypeScript check and build

```powershell
pnpm --prefix frontend exec tsc --noEmit
pnpm --prefix frontend build
```

Both pass with no errors.

### Browser E2E tests (Playwright — requires running backend)

```powershell
# Start backend first: uvicorn backend.app.main:app --port 8000
playwright install chromium
pytest backend/tests/e2e/ -ra -v
```

14 tests covering: staff page smoke, mobile hamburger toggle, recovery page at 380px, offer acceptance flow, duplicate rejection, invalid token error state.

**Status:** Tests are written and collected. Run against live server — see [docs/TESTING.md](docs/TESTING.md) for current results.

### CI

GitHub Actions workflow: `.github/workflows/ci.yml`
- **backend job**: PostgreSQL service, ruff lint, Alembic migration validation, pytest
- **frontend job**: pnpm frozen install, tsc, vite build
- **e2e job**: runs after backend+frontend, Playwright chromium tests

**Status:** Workflow is committed and configured. Remote run not yet verified (no GitHub push performed).

---

## Demo Data Policy

- **No seed script** — the app does not populate demo data automatically.
- **No mock arrays in frontend** — all pages fetch from the API. An empty database renders empty states, not fake data.
- **Test fixtures** (in `conftest.py` and individual test files) create records in `slotback_test`, not the development database. The safety guard in `conftest.py` raises `RuntimeError` if tests would run against `slotback`.
- **Notification "delivery"** is simulated — the `NotificationLog.status` field records `delivered` or `failed` based on the toggle, but no real email is sent. This is clearly labeled in the UI and code.

---

## Security Limitations & Known Issues

> [!CAUTION]
> **Not production-ready.** The following blockers must be resolved before any public deployment.

| Issue | Severity | Status |
|---|---|---|
| **No staff authentication** — all `/api/v1` endpoints (except `/offer/:token` and `/book`) are publicly accessible | 🔴 Release blocker | Not implemented |
| **Simulated notifications** — no real email delivery | 🟡 Feature gap | Documented, labeled |
| `allow_origins: ["*"]` fallback in CORS when `CORS_ORIGINS` is empty | 🟡 Configuration risk | Must set `CORS_ORIGINS` in production |
| `DEBUG=true` must be `false` in production | 🟡 Configuration | Set via env var |
| No HTTPS enforcement in app code | 🟡 Infrastructure | Use reverse proxy (nginx/caddy) |
| Staff endpoint authorization (per-business tenant isolation) | 🔴 Future feature | Not scoped |

---

## Deployment Status

**Not deployed.** No public URL exists.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the deployment plan covering Railway/Render + managed PostgreSQL, required env vars, migration steps, health check, and security prerequisites.

**Blocking before any production deployment:**
1. Implement staff authentication (e.g., simple API key or OAuth).
2. Set `CORS_ORIGINS` to the exact frontend domain.
3. Set `DEBUG=false` and `APP_ENV=production`.
4. Verify `alembic upgrade head` on a fresh production database.
5. Confirm CI passes on the remote repository.

---

## Configuration Reference

All configuration is through environment variables (no config files with secrets):

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string (`postgresql+psycopg://...`) |
| `TEST_DATABASE_URL` | Tests | Separate test DB; safety guard prevents using main DB |
| `APP_NAME` | | Defaults to `SlotBack` |
| `APP_ENV` | | `development` / `test` / `production` |
| `DEBUG` | | `true` only in development |
| `API_V1_PREFIX` | | Defaults to `/api/v1` |
| `CORS_ORIGINS` | | Comma-separated origins; use exact domains in production |
| `LOG_LEVEL` | | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## Detailed Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Component diagram, API flow, domain rules, concurrency
- [docs/TESTING.md](docs/TESTING.md) — Test categories, isolation, commands, coverage, results, known gaps
- [docs/METRICS.md](docs/METRICS.md) — Metric definitions, formulas, source tables, limitations
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Prerequisites, env vars, DB provisioning, steps, rollback
- [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) — Product scope and roadmap
