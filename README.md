# SlotBack

Appointment cancellation-recovery for small service businesses. When a booking is cancelled, SlotBack matches the released slot to an eligible waitlisted customer, issues a time-limited offer, and confirms at most one replacement booking.

**Users:** service-business staff (portal) and customers (booking / offer pages).

## Architecture
React + TypeScript + Vite → FastAPI (`/api/v1`) → service layer → SQLAlchemy → PostgreSQL (Alembic migrations). In local/prod-style runs, FastAPI also serves the built frontend from `frontend/dist`. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Prerequisites (verified locally)
Python 3.12, Node 24 (pnpm via `npx pnpm`), PostgreSQL running locally.

## Local setup
```powershell
# 1. Environment (fill values; never commit .env)
copy .env.example .env      # set DATABASE_URL, CORS_ORIGINS

# 2. Backend deps + DB
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/setup_postgres.py   # creates non-superuser role + dbs (local dev only)
.venv\Scripts\alembic upgrade head

# 3. Frontend build
cd frontend; npx pnpm install; npx pnpm exec vite build; cd ..

# 4. Run (serves API + UI)
.venv\Scripts\uvicorn backend.app.main:app --reload --port 8000
```
Open http://localhost:8000 (staff portal), http://localhost:8000/book (customer booking), http://localhost:8000/docs (OpenAPI).
For frontend hot-reload instead: `cd frontend; npx pnpm dev` → http://localhost:5173 (proxies `/api` to :8000).

## Product flow
1. Staff (or customer via `/book`) creates an appointment; the server rejects overlapping bookings for the same service (409).
2. Staff cancels it → slot released.
3. If auto-match is on (Settings), the oldest active waitlist entry for that service whose preferred window covers the slot receives an offer; staff can also issue offers manually on **Slot Recovery**.
4. Customer opens `/offer/<token>`, sees expiry countdown, accepts.
5. Server locks the offer and appointment rows (`SELECT … FOR UPDATE`), re-checks status and expiry, and confirms. Repeat acceptance → 400; expired → 400.
6. Reports/Overview metrics are computed from the database at request time.

## Screens
Overview (workload, urgent cancellations, active offers, notification failures) · Appointments (search/filter, book, cancel) · Waitlist (add/remove entries) · Slot Recovery (released slots, issue/withdraw offers, retry failed notifications) · Reports (recovery rate with denominator, median time to refill, failure rate) · Settings (business prefs, services) · `/book` · `/offer/:token`.

## Testing
See [docs/TESTING.md](docs/TESTING.md).
```powershell
.venv\Scripts\pytest -q                      # backend unit + API integration (PostgreSQL)
cd frontend; npx pnpm exec tsc --noEmit; npx pnpm exec vite build
```
Browser (Playwright) automation: **not implemented**. "E2E" backend tests are HTTP-level API tests.

## Demo data
There is no seed script and no frontend mock data: every screen reads from the API. An empty database shows empty states. Test runs currently write to the database in `DATABASE_URL` (see limitations).

## Known limitations
- **No authentication/authorization** on staff endpoints — not production-ready.
- Tests use the main `DATABASE_URL`, not a separate test database (violates AGENTS.md; pending).
- "Simulate notification failure" is a staff testing toggle; no real email provider is integrated — delivery status is recorded, not actually sent.
- Notification retry marks delivery as delivered without a real send.
- Appointments table is horizontally scrollable on mobile rather than a card list.
- No deployment verified; CI does not run frontend checks.

## Configuration
Env var names only: `APP_NAME`, `APP_ENV`, `DEBUG`, `API_V1_PREFIX`, `DATABASE_URL`, `CORS_ORIGINS`, `LOG_LEVEL`. Deployment: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Metrics: [docs/METRICS.md](docs/METRICS.md).
