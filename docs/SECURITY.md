# SlotBack — Security & Release Readiness Assessment

## Database Permissions (Verified)
- **Least Privilege Enforcement**: The application connects to PostgreSQL via a dedicated `slotback` user.
- **Superuser Removal**: The `slotback` role explicitly lacks `SUPERUSER` privileges (`NOSUPERUSER`), as enforced by the `setup_postgres.py` configuration script.
- **Schema Ownership**: The `slotback` database and schema are owned by the `slotback` role, isolating it from other databases.

## Secret Handling (Verified)
- **Environment Isolation**: No hardcoded credentials exist in source code. All configurations are loaded via `backend/app/core/config.py` from `.env`.
- **Repository Safety**: A template `.env.example` is provided, and actual `.env` files are ignored by git to prevent accidental secret leakage.

## Backend Validation & Authorization Boundaries (Verified)
- **Direct API & Manipulated Request Protection**: The backend enforces strict validation on all offer creation requests (`POST /api/v1/recovery/offers`). Even if the client bypasses the frontend and submits manipulated payloads:
  - Waitlist service mismatch is rejected (`HTTP 400 Bad Request`).
  - Appointment start time outside the customer's preferred date window is rejected (`HTTP 400 Bad Request`).
  - Ineligible or already-fulfilled waitlist status is rejected (`HTTP 400 Bad Request`).
- **Overlapping Booking Prevention**: The backend verifies time slot availability before creating appointments, returning `HTTP 409 Conflict` for overlapping intervals on the same service.

## Concurrency & Data Integrity (Verified)
- **Atomic Acceptance**: Verified. The `accept_offer` method uses `SELECT ... FOR UPDATE` to lock both the `RecoveryOffer` and associated `Appointment` rows simultaneously in a database transaction.
- **Duplicate Acceptance Prevention**: Submitting duplicate acceptance requests returns `HTTP 400 Bad Request` ("already been accepted").
- **Test Database Isolation**: `conftest.py` and `e2e/conftest.py` verify that tests cannot run against `/slotback` (the development database), raising an immediate `RuntimeError` if an unsafe database URL is detected.

## Authentication Blockers for Public Release (HARD RELEASE BLOCKER)
Currently, **ALL** endpoints under `/api/v1` are publicly accessible without authentication. This is a critical release blocker before public production deployment.

### Required Actions Before Public Release:
1. **Staff API Protection**: All staff-facing routes (`/services`, `/appointments`, `/waitlist`, `/reports`, `/settings`, `/recovery/offers` creation/withdrawal) must be protected behind an authentication barrier (e.g., JWT Bearer tokens or secure session cookies).
2. **Customer Capability Token Model**: The customer endpoints `/recovery/offers/{token}` and `/recovery/offers/{token}/accept` should remain accessible only via the unguessable cryptographically random UUID token (`uuid4`), which serves as a one-time capability URL.
3. **Role-Based Access Control (RBAC)**: Enforce staff-only permissions server-side on administrative actions.
4. **DO NOT DEPLOY PUBLICLY**: SlotBack is suitable only for private local evaluation until staff authentication and RBAC are implemented.

