# SlotBack — Production Readiness Security, Architecture & Reliability Audit (Phase 1)

**Audit Date:** 2026-10-10  
**Auditors:** Application Security, Senior Backend & DevOps Engineering  
**Scope:** All FastAPI routes, SQLAlchemy models, Pydantic schemas, Service layer, Database configuration, Alembic migrations, Frontend API integration, Environment settings, Test suites, and GitHub Actions CI.

---

## Executive Summary

SlotBack provides an appointment cancellation recovery system for service businesses. While core recovery logic and atomic locking for offer acceptance (`SELECT ... FOR UPDATE`) are implemented, the application in its current state is **NOT PRODUCTION-READY** due to critical release-blocking architectural and security vulnerabilities:
1. **Zero Authentication & Authorization**: Every API route under `/api/v1` is publicly accessible without credentials. Any unauthenticated caller can view, modify, or delete appointments, waitlist customers, and business settings.
2. **Missing Multi-Tenant Scoping**: Models lack business ownership scoping, exposing data to cross-tenant leakage.
3. **Empty Alembic Migrations**: Alembic version `5910adfcb702` contains a no-op migration (`pass`), while the app relies on startup `create_all()`.
4. **Missing Rate Limiting**: Abuse-prone public endpoints and capability-token URLs lack throttling.
5. **Simulated Notification Delivery**: The notification subsystem currently fakes delivery status based on client payload booleans rather than interfacing with a bounded, resilient email provider.

---

## Detailed Findings Matrix

| Finding ID | Domain | Issue | Severity | Status |
|---|---|---|---|---|
| **AUD-01** | Auth & Access Control | Complete absence of staff authentication & authorization | **CRITICAL** | Release Blocker |
| **AUD-02** | Multi-Tenancy | Lack of tenant/business scoping on domain records | **HIGH** | Architecture Risk |
| **AUD-03** | Schema / Migrations | Empty Alembic migration with reliance on startup `create_all` | **HIGH** | Production Blocker |
| **AUD-04** | Abuse / Availability | No rate limiting on public booking and offer acceptance endpoints | **HIGH** | Security Risk |
| **AUD-05** | Notifications | Simulated email delivery without bounded retry or actual provider | **HIGH** | Reliability Deficit |
| **AUD-06** | Concurrency | `create_appointment` lacks row/table locks against concurrent slot collisions | **MEDIUM** | Race Condition Risk |
| **AUD-07** | Configuration / Secrets | Production config missing fail-safe validation (secret key, debug mode, CORS wildcard) | **HIGH** | Security Risk |
| **AUD-08** | Monitoring / Health | Health check `/health` does not verify database connectivity | **MEDIUM** | Operational Deficit |
| **AUD-09** | Input Validation | Pydantic schemas do not forbid extra fields or enforce past-date guards on bookings | **LOW** | Hardening Needed |
| **AUD-10** | CI / Pipeline | CI migration step runs empty revision, masking schema drift | **MEDIUM** | Reliability Deficit |

---

## Detailed Analysis by Category

### 1. Missing Authentication & Authorization (AUD-01)
- **Severity**: CRITICAL
- **Affected Files**: `backend/app/api/v1/endpoints.py`, `backend/app/main.py`
- **Affected Routes**:
  - `GET`, `POST` `/api/v1/services`, `PUT /api/v1/services/{id}`
  - `GET`, `POST` `/api/v1/appointments`, `POST /api/v1/appointments/{id}/cancel`
  - `GET`, `POST` `/api/v1/waitlist`, `DELETE /api/v1/waitlist/{id}`
  - `GET`, `POST` `/api/v1/recovery/offers`, `POST /api/v1/recovery/offers/{id}/withdraw`, `POST /api/v1/recovery/notifications/{id}/retry`
  - `GET /api/v1/reports/metrics`
  - `GET`, `PUT` `/api/v1/settings`
- **Evidence**: `endpoints.py` defines route dependencies taking only `db: Session = Depends(get_db)`. No security dependency (`OAuth2PasswordBearer`, HTTPBearer, or session cookie verification) exists on any route.
- **Impact**: Any anonymous actor on the internet can cancel all appointments, read customer PII (names, emails, phone numbers), manipulate business settings, and issue unauthorized offers.
- **Remediation**:
  - Implement staff authentication with JWT Bearer tokens and PBKDF2/Argon2 password hashing.
  - Require authenticated staff identity on all management endpoints by default.
  - Enforce Role-Based Access Control (RBAC): `admin` role required for modifying settings and services; `staff` permitted for day-to-day operations.
  - Retain capability-token access only for `GET /api/v1/recovery/offers/{token}` and `POST /api/v1/recovery/offers/{token}/accept`.
  - Retain public customer self-service access for creating appointments (`POST /api/v1/appointments`), waitlist entries (`POST /api/v1/waitlist`), and querying active services (`GET /api/v1/services?active_only=true`) behind strict rate limiting.

### 2. Cross-Business Data-Access Risks (AUD-02)
- **Severity**: HIGH
- **Affected Files**: `backend/app/models/domain.py`, `backend/app/services/recovery_service.py`
- **Evidence**: `Service`, `Appointment`, `WaitlistEntry`, `RecoveryOffer`, and `NotificationLog` have no `business_id` foreign key. `BusinessSetting` uses a static primary key `id = 1`.
- **Impact**: If multiple service businesses share an instance, one business could view and modify another business's customers, bookings, and revenue metrics.
- **Remediation**:
  - Add `business_id` scoping to domain queries or architect tenant scoping into all service layer calls.
  - Associate staff users with a specific `business_id`.
  - Verify tenant ownership on every read and write operation.

### 3. Database Migrations, Schema & Startup (AUD-03)
- **Severity**: HIGH
- **Affected Files**: `backend/alembic/versions/5910adfcb702_initial_schema.py`, `backend/app/main.py:17`
- **Evidence**:
  ```python
  # 5910adfcb702_initial_schema.py
  def upgrade() -> None:
      pass
  def downgrade() -> None:
      pass
  ```
  `main.py` calls `Base.metadata.create_all(bind=engine)` inside the FastAPI lifespan startup.
- **Impact**: In production, running `alembic upgrade head` creates no tables. If startup lacks table creation privileges (least privilege DB user), the application crashes. Furthermore, schema modifications cannot be deployed safely through version control without real migrations.
- **Remediation**:
  - Generate a full, complete initial schema Alembic migration containing all tables, columns, indexes, and constraints.
  - Document explicit migration execution prior to application startup.
  - Provide a migration for user authentication and staff accounts.

### 4. Public Endpoint Abuse & Rate Limiting (AUD-04)
- **Severity**: HIGH
- **Affected Files**: `backend/app/main.py`, `backend/app/api/v1/endpoints.py`
- **Evidence**: No rate limiting middleware or throttling headers exist.
- **Impact**: Attackers can brute-force login credentials, exhaust database connection pools by spamming appointment creations, or attempt token guessing attacks against the offer endpoint.
- **Remediation**:
  - Add rate limiting middleware enforcing IP-based requests-per-minute quotas on sensitive endpoints:
    - `/api/v1/auth/login`: 5 requests/minute
    - `/api/v1/recovery/offers/{token}/accept`: 10 requests/minute
    - Public booking / waitlist creation: 20 requests/minute

### 5. Notification Delivery & Retry Behavior (AUD-05)
- **Severity**: HIGH
- **Affected Files**: `backend/app/services/recovery_service.py:337-353, 435-453`
- **Evidence**:
  ```python
  notif_status = "failed" if data.simulate_notification_failure else "delivered"
  ```
  `retry_notification` unconditionally marks `log.status = "delivered"` without dispatching an email.
- **Impact**: Staff are presented with simulated deliverability metrics that do not reflect reality. If a real provider fails, there is no backoff or bounded retry limit.
- **Remediation**:
  - Implement a pluggable `EmailProvider` interface supporting standard SMTP credentials via environment variables (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`) and structured logging fallback when credentials are not configured.
  - Decouple notification dispatch so email network timeouts or failures never abort database transactions.
  - Implement bounded retries (maximum 3 retries) and record actual errors.

### 6. Booking Conflicts, Transaction Safety & Idempotency (AUD-06)
- **Severity**: MEDIUM
- **Affected Files**: `backend/app/services/recovery_service.py:101-111, 359-418`
- **Evidence**:
  - `accept_offer` correctly uses `SELECT ... FOR UPDATE` on both `RecoveryOffer` and `Appointment` within a transaction.
  - `create_appointment` performs a `SELECT` conflict check followed by `db.add()`, without table or row locking. Concurrent requests for the same time slot can create overlapping appointments.
- **Remediation**:
  - Implement explicit conflict locking or check constraints for concurrent booking safety.
  - Ensure idempotent responses on duplicate accept requests.

### 7. Configuration, CORS, Debug Mode & Secret Handling (AUD-07)
- **Severity**: HIGH
- **Affected Files**: `backend/app/core/config.py`, `backend/app/main.py:29-36`, `.env.example`
- **Evidence**:
  - `cors_origins` defaults to `"http://localhost:5173"`, but fallback allows `["*"]` with `allow_credentials=True`.
  - `.env.example` sets `DEBUG=true`.
  - `Settings` lacks a `SECRET_KEY` field for signing authentication tokens.
- **Remediation**:
  - Add `secret_key` with high-entropy validation.
  - Enforce fail-safe validation in `production` environment: reject default secret keys, disable `debug`, and disallow wildcard CORS origins when credentials are enabled.

### 8. Monitoring & Readiness Separation (AUD-08)
- **Severity**: MEDIUM
- **Affected Files**: `backend/app/main.py:39-41`
- **Evidence**: `/health` simply returns `{"status": "ok"}` without testing whether PostgreSQL is reachable.
- **Impact**: Kubernetes or process orchestrators will route customer traffic to instances that cannot talk to the database.
- **Remediation**:
  - Keep `/health` or `/health/live` for process liveness.
  - Add `/health/ready` verifying database connectivity (`SELECT 1`).

### 9. Input Validation & Mass-Assignment Risks (AUD-09)
- **Severity**: LOW
- **Affected Files**: `backend/app/schemas/domain.py`
- **Evidence**: Schemas do not specify `extra="forbid"`, which could permit unforeseen client parameters. `AppointmentCreate` does not assert `start_time > now`.
- **Remediation**:
  - Apply `extra="forbid"` to critical request schemas.
  - Enforce validation rules on scheduling intervals.

### 10. CI / Migration Testing (AUD-10)
- **Severity**: MEDIUM
- **Affected Files**: `.github/workflows/ci.yml:48, 129`
- **Evidence**: `alembic upgrade head` runs against a clean database in CI, but passes silently because the migration file is empty (`pass`).
- **Remediation**:
  - Ensure real migrations exist so Alembic actually creates all schema elements during CI.
