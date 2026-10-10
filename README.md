# SlotBack — Appointment Cancellation Recovery

**Recover cancelled appointments. Reduce unused capacity. Turn waitlists into completed bookings.**

SlotBack is a full-stack appointment recovery system designed for small service businesses. When a customer cancels an appointment, SlotBack helps staff identify eligible waitlisted customers, issue time-limited recovery offers, and refill released appointment slots.

Instead of treating cancellations as lost capacity, SlotBack provides a structured workflow for matching customers, managing offers, tracking recovery outcomes, and monitoring operational performance.

## Problem

Appointment cancellations create unexpected gaps in business schedules. Manually contacting waitlisted customers is time-consuming, inconsistent, and difficult to track.

SlotBack addresses this by connecting appointment management, waitlist matching, recovery offers, and reporting in one application.

## Features

- **Appointment management** — Create, view, and cancel appointments.
- **Waitlist management** — Maintain customer preferences and service requirements.
- **Automated recovery matching** — Match cancelled slots with eligible waitlist entries.
- **Manual recovery matching** — Allow staff to initiate recovery offers.
- **Time-limited offers** — Generate unique offer tokens with expiry rules.
- **Safe offer acceptance** — Validate offer status and prevent duplicate acceptance.
- **Operational dashboard** — Track cancellations, active offers, and recovery metrics.
- **Recovery reporting** — Measure recovered appointments, recovery rates, and time to refill.
- **Notification tracking** — Record notification outcomes and failures.
- **Business settings** — Configure automatic matching and offer-expiry behavior.

## Technology Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React, TypeScript | User interface and application state |
| Build tooling | Vite | Development server and production builds |
| Routing | React Router | Staff and customer-facing routes |
| Styling | CSS | Responsive layouts and reusable visual styles |
| Backend | Python, FastAPI | REST API and request handling |
| Validation | Pydantic v2 | Request and response schemas |
| Business logic | SlotBackService | Appointment, waitlist, and recovery rules |
| ORM | SQLAlchemy 2.x | Database access and transactions |
| Database | PostgreSQL | Persistent application data |
| Migrations | Alembic | Version-controlled schema changes |
| Testing | Pytest, Vitest, Playwright | Backend, frontend, and browser-level verification |

## Architecture

SlotBack follows a three-tier architecture with a separate frontend, backend API, and relational database. Business rules are centralized in a service layer rather than embedded in frontend components or API handlers.

```text
┌──────────────────────────────────────┐
│           Presentation Layer         │
│                                      │
│       React + TypeScript + Vite      │
│            React Router              │
│                                      │
│   Staff Portal     Customer Pages    │
└───────────────────┬──────────────────┘
                    │
                    │ HTTP / JSON
                    ▼
┌──────────────────────────────────────┐
│             API Layer                │
│                                      │
│              FastAPI                 │
│          /api/v1 endpoints            │
│                                      │
│   Request validation and responses   │
└───────────────────┬──────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
│           Service Layer              │
│                                      │
│           SlotBackService             │
│                                      │
│   Appointment and waitlist rules     │
│   Recovery matching and offer logic  │
│   Status transitions and metrics     │
└───────────────────┬──────────────────┘
                    │
                    │ SQLAlchemy
                    ▼
┌──────────────────────────────────────┐
│             Data Layer               │
│                                      │
│              PostgreSQL              │
│                                      │
│ Services · Appointments · Waitlist   │
│ Offers · Notification Logs · Settings│
│                                      │
│        Alembic schema migrations     │
└──────────────────────────────────────┘
```

### Frontend

The React frontend is responsible for rendering pages, collecting user input, managing navigation, and displaying API responses.

The application separates reusable UI components from page-specific functionality.

| Component | Responsibility |
|---|---|
| `App.tsx` | Route definitions and staff layout |
| `api/client.ts` | Centralized HTTP communication with the backend |
| `components/` | Navigation, modals, status badges, loading states, and empty states |
| `pages/OverviewPage.tsx` | Dashboard and operational metrics |
| `pages/AppointmentsPage.tsx` | Appointment operations |
| `pages/WaitlistPage.tsx` | Waitlist management |
| `pages/RecoveryPage.tsx` | Recovery offers and matching workflow |
| `pages/ReportsPage.tsx` | Recovery reporting |
| `pages/SettingsPage.tsx` | Business configuration |
| `pages/CustomerBookingPage.tsx` | Customer booking interface |
| `pages/CustomerOfferPage.tsx` | Customer recovery-offer acceptance |
| `types/index.ts` | Shared TypeScript types |
| `index.css` | Design tokens, layouts, tables, forms, and responsive styles |

The staff portal and customer-facing pages share the frontend application but use separate routes.

### Backend

The FastAPI backend exposes HTTP endpoints and coordinates application operations. Its service layer contains the core domain rules, keeping endpoint handlers focused on request validation, delegation, and responses.

| Module | Responsibility |
|---|---|
| `backend/app/main.py` | Application initialization, middleware, and frontend serving configuration |
| `backend/app/api/v1/endpoints.py` | Versioned API endpoints |
| `backend/app/services/recovery_service.py` | Appointment, waitlist, recovery, settings, and reporting logic |
| `backend/app/models/domain.py` | SQLAlchemy database models |
| `backend/app/schemas/domain.py` | Pydantic request and response schemas |
| `backend/app/db/session.py` | Database engine and session management |
| `backend/app/core/config.py` | Environment-based application configuration |

### Database

PostgreSQL is the authoritative data store. SQLAlchemy maps application entities to relational tables, while Alembic manages database schema migrations.

| Entity | Purpose |
|---|---|
| `services` | Service definitions and durations |
| `appointments` | Customer bookings, cancellation details, and recovery status |
| `waitlist_entries` | Customer preferences and waitlist state |
| `recovery_offers` | Offer tokens, expiry, acceptance, and status |
| `notification_logs` | Notification delivery outcomes and retry information |
| `business_settings` | Automatic matching and default offer-expiry settings |

Related state changes are handled transactionally so appointment, offer, and waitlist records remain consistent.

## How Frontend and Backend Communicate

The frontend communicates with FastAPI through HTTP requests and JSON responses.

```text
User interaction
      │
      ▼
React page or component
      │
      ▼
api/client.ts
      │
      ▼
FastAPI endpoint
      │
      ▼
Pydantic validation
      │
      ▼
SlotBackService
      │
      ▼
SQLAlchemy session
      │
      ▼
PostgreSQL
      │
      ▼
JSON response
      │
      ▼
React updates the interface
```

During local development, Vite proxies `/api` requests to the FastAPI server running on port `8000`. The frontend development server runs on port `5173`.

FastAPI also exposes interactive API documentation at `/docs`.

## Core Workflow: Cancellation to Recovery

The main business workflow is designed to refill a released appointment slot without relying on unrestricted manual coordination.

1. **Cancellation:** A staff member cancels an appointment. The cancellation status, timestamp, and reason are recorded.
2. **Eligibility matching:** If automatic matching is enabled, the service searches for active waitlist entries matching the service and preferred appointment window.
3. **Offer creation:** The eligible customer receives a recovery offer with a unique token and expiry timestamp.
4. **Customer response:** The customer opens the offer page and accepts before the offer expires.
5. **Transactional confirmation:** The backend locks the relevant offer and appointment records, revalidates their states, and applies the related changes in a database transaction.
6. **State synchronization:** The appointment is reassigned, the offer is marked accepted, and the waitlist entry is fulfilled.
7. **Reporting:** Recovery metrics are derived from persisted application data.

### Recovery Integrity

Offer acceptance is a critical operation because two requests could attempt to claim the same appointment.

SlotBack uses database row locking (`SELECT ... FOR UPDATE`) and transactional validation to reduce race conditions. The backend rechecks the offer status and expiry before committing the changes, preventing an already accepted or expired offer from being accepted again.

The frontend improves usability, but the backend remains responsible for enforcing business rules and maintaining data integrity.

## Repository Structure

```text
SlotBack/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   └── tests/
│       ├── unit/
│       ├── api/
│       └── e2e/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   ├── ARCHITECTURE.md
│   ├── TESTING.md
│   ├── METRICS.md
│   ├── DEPLOYMENT.md
│   └── PROJECT_OVERVIEW.md
├── .github/workflows/
├── alembic.ini
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Node.js 20+
- pnpm 9+

### 1. Clone the repository

```bash
git clone https://github.com/Bhavadharani412/SlotBack.git
cd SlotBack
```

### 2. Configure environment variables

Create a local environment file from the example:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

Configure the required values in `.env`:

```dotenv
APP_NAME=SlotBack
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/slotback
TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/slotback_test

CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```

Replace the database credentials with your local PostgreSQL configuration. Create the development and test databases before running the application.

**Never commit `.env` or production credentials.**

### 3. Install backend dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
```

### 4. Apply database migrations

```powershell
alembic upgrade head
```

### 5. Start the backend

```powershell
uvicorn backend.app.main:app --reload --port 8000
```

The API should be available at:

- Application health: `http://localhost:8000/health`
- Interactive API documentation: `http://localhost:8000/docs`

### 6. Start the frontend

Open another terminal:

```powershell
pnpm --dir frontend install
pnpm --dir frontend dev
```

Open `http://localhost:5173` in your browser.

### 7. Build the frontend

```powershell
pnpm --dir frontend build
```

The production build is generated in `frontend/dist`. When configured for production, the FastAPI application can serve the built frontend alongside the API.

## Testing

SlotBack separates business-rule tests, API integration tests, and browser-level end-to-end tests.

### Backend unit tests

```powershell
pytest backend/tests/unit/ -ra -v
```

### API integration tests

```powershell
pytest backend/tests/api/ -ra -v
```

These tests require a correctly configured, separate PostgreSQL test database.

### Full backend suite

```powershell
pytest -ra -v
```

### Frontend type-check and build

```powershell
pnpm --dir frontend exec tsc --noEmit
pnpm --dir frontend build
```

### Browser end-to-end tests

With the backend running and Playwright's browser installed:

```powershell
pytest backend/tests/e2e/ -ra -v
```

The browser suite covers critical application interactions, including recovery flows and offer acceptance.

See [docs/TESTING.md](docs/TESTING.md) for test isolation, coverage by scenario, and verification results. Test outcomes should be recorded from actual runs rather than inferred from the presence of test files.

## Engineering Principles

- **Separation of concerns:** UI, API handlers, business logic, and persistence have distinct responsibilities.
- **Data integrity:** Related recovery operations use transactions and database-level locking where needed.
- **Backend validation:** Client-side validation improves usability but does not replace server-side checks.
- **Explicit persistence:** PostgreSQL is the authoritative database; SQLite is not a silent fallback.
- **Reproducible schema changes:** Database changes are managed through Alembic migrations.
- **Test isolation:** Automated tests use a separate database to protect development data.
- **Configuration hygiene:** Secrets and environment-specific settings stay outside committed source code.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Testing](docs/TESTING.md)
- [Metrics](docs/METRICS.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Project Overview](docs/PROJECT_OVERVIEW.md)

## Project Status

SlotBack is being developed as an operational tool for appointment cancellation recovery. Its core design focuses on waitlist eligibility, offer expiry, transactional acceptance, and measurable recovery outcomes.

Production readiness depends on verifying deployment configuration, migrations, authorization, and real notification delivery in the target environment. Notification logs and simulated delivery outcomes should not be interpreted as proof of successful real-world email delivery.

## License

Add a license file and specify the license here before distributing the project for reuse.
