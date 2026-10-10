# SlotBack — Architecture and Product Engineering

## 1. Architecture Overview

SlotBack uses a layered architecture with a React frontend, a Python API and PostgreSQL as the source of truth.

```text
React + TypeScript
        |
        | HTTPS / REST / JSON
        v
FastAPI Application
        |
        +-- Authentication and Authorization
        +-- Appointment API
        +-- Waitlist and Recovery API
        +-- Notification API
        +-- Metrics API
        |
        v
Application Services
        |
        +-- Booking Service
        +-- Recovery Service
        +-- Notification Service
        +-- Metrics Service
        |
        v
SQLAlchemy / Alembic
        |
        v
PostgreSQL
```

External email delivery is handled through a notification provider. GitHub Actions validates code and manages the release workflow.

## 2. Frontend Engineering

### Responsibilities

The frontend owns presentation, navigation, form interaction and client-side feedback. Business rules and authorization remain enforced by the backend.

### Product Experience

The interface should be modern, responsive and task-oriented.

- **Staff dashboard:** Today's appointments, cancellations, pending offers and recovery metrics.
- **Appointment calendar:** Availability, booking status and appointment details.
- **Waitlist management:** Eligible customers, requested time windows and offer status.
- **Customer booking:** Service selection, available slots and booking confirmation.
- **Recovery experience:** Clear offer expiry, acceptance status and confirmation feedback.

Use reusable React components, typed API contracts, accessible forms, loading states, empty states and meaningful error messages. Avoid presenting placeholder analytics as real data.

## 3. Backend Engineering

FastAPI exposes versioned REST endpoints under `/api/v1`.

The backend is divided into four responsibilities:

- **API layer:** HTTP routing, request validation, authentication and response formatting.
- **Service layer:** Booking rules, eligibility, offer acceptance and metric calculations.
- **Data layer:** Database queries, transactions and persistence.
- **Infrastructure layer:** Configuration, logging, email integration and error handling.

Business rules belong in the service layer rather than being duplicated across route handlers.

Database transactions must cover related state changes. External notifications should not be sent while holding database locks. Where reliability requires it, use a transactional outbox and an idempotent worker to deliver pending notifications.

## 4. Database Design

Initial entities:

| Entity | Responsibility |
|---|---|
| `users` | Customer and staff identities |
| `services` | Bookable business services and durations |
| `availability` | Valid bookable time windows |
| `appointments` | Booking lifecycle and assigned time slot |
| `waitlist_entries` | Customer preferences and eligibility |
| `recovery_offers` | Offered slots, recipients, expiry and outcomes |
| `notification_events` | Delivery attempts, outcomes and errors |
| `audit_events` | Important state changes for investigation |

Use foreign keys, appropriate indexes, timestamps and database constraints. Store timestamps consistently in UTC and convert them for display in the user's local timezone.

Use explicit lifecycle states instead of inferring state from missing fields.

## 5. Critical Product Invariants

These rules must hold regardless of which frontend or API client makes a request.

1. A slot cannot have overlapping confirmed appointments where the service and resource constraints prohibit overlap.
2. A recovery offer must refer to a valid released slot and an eligible recipient.
3. An expired, withdrawn or already-consumed offer cannot be accepted.
4. An appointment cannot be confirmed twice.
5. Customers cannot access or accept offers belonging to other customers.
6. Repeated requests must not duplicate bookings or recovery side effects.
7. Failed notifications must be observable and recoverable.
8. Dashboard metrics must be derived from persisted records and documented definitions.

Enforce these rules through authorization, service-layer validation, transactions and database constraints as appropriate. Use row locking, conditional updates or another justified concurrency-control strategy for competing acceptance requests.

## 6. API Design

All application endpoints use `/api/v1`.

Initial resource groups:

- `/auth` — authentication and session management.
- `/services` — service definitions.
- `/availability` — available appointment slots.
- `/appointments` — booking, cancellation and rescheduling.
- `/waitlist` — waitlist entry management.
- `/recovery-offers` — offer listing and acceptance.
- `/notifications` — authorized delivery status.
- `/metrics` — aggregated operational metrics.
- `/health` — application health checks.

Use appropriate HTTP methods and status codes, consistent error responses, pagination where necessary and explicit authorization requirements.

FastAPI generates the OpenAPI contract. Document authentication, request and response schemas, failure cases and example requests.

## 7. Product Engineering Decisions

- PostgreSQL is the authoritative source for booking state.
- Availability shown in the browser is advisory; the server validates it again during booking.
- Time-limited offers have explicit expiry and acceptance rules.
- Notification delivery is separate from booking confirmation.
- Metrics use documented event definitions rather than frontend counters.
- Secrets are supplied through environment configuration and never committed.
- Schema changes use versioned migrations.
- Critical operations produce structured logs and traceable identifiers.
- The initial implementation prioritizes a single business workflow while keeping data ownership boundaries explicit.

## 8. Deployment Boundaries

Deploy the frontend and API independently. The API connects to managed PostgreSQL using a restricted database account and securely configured connection settings.

Use separate test and production environments. Run migrations as a controlled release step, validate health checks and execute production smoke tests after deployment.

## 9. Architecture Acceptance Criteria

The architecture is acceptable when:

- Frontend and backend responsibilities are clearly separated.
- Core business rules can be tested independently.
- Database migrations recreate the required schema.
- Concurrent booking operations preserve all critical invariants.
- API contracts are documented and testable.
- Failures are observable without exposing sensitive information.
- A new developer or coding agent can set up and run the application using documented instructions.