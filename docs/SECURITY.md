# SlotBack — Security & Release Readiness Assessment

## Database Permissions (Verified)
- **Least Privilege Enforcement**: The application connects to PostgreSQL via a dedicated `slotback` user.
- **Superuser Removal**: The `slotback` role explicitly lacks `SUPERUSER` privileges (`NOSUPERUSER`), as enforced by the `setup_postgres.py` configuration script.
- **Schema Ownership**: The `slotback` database and schema are owned by the `slotback` role, isolating it from other databases.

## Secret Handling & Environment Isolation (Verified)
- **Zero Secrets in Source Control**: All sensitive values are loaded dynamically from environment variables via Pydantic v2 `BaseSettings`.
- **Production Validation Guard**: `Settings.validate_production_configuration()` executes at application startup in `production`. It halts process initialization with a fatal `ValueError` if:
  - `SECRET_KEY` is set to the default development placeholder or is under 32 characters.
  - `DEBUG` is set to `True`.
  - `CORS_ORIGINS` contains wildcard `'*'` while credentials are enabled.

## Authentication & Session Handling (Verified)
- **Staff Authentication Barrier**: All management endpoints (`/appointments`, `/waitlist`, `/recovery/offers`, `/reports`, `/settings`, `/auth/me`) require valid JWT Bearer tokens signed with HMAC-SHA256. Anonymous requests return `HTTP 401 Unauthorized`.
- **Password Hashing**: NIST/OWASP compliant PBKDF2-HMAC-SHA256 with 600,000 iterations and 16-byte cryptographically random salt (`secrets.token_bytes(16)`). Constant-time verification prevents timing attacks.
- **Token Invalidation**: Expired, malformed, or tampered JWTs are rejected with `HTTP 401 Unauthorized` and `WWW-Authenticate: Bearer`.
- **Initial Administrator Provisioning**: If the `users` table is empty on startup, the application creates an initial administrative account configured via `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD`.

## Role-Based Access Control (RBAC) (Verified)
- **Granular Roles**: Server-side role checks enforce distinction between `admin` and `staff`:
  - **Admin-only operations (`HTTP 403 Forbidden` for regular staff)**: Service creation (`POST /api/v1/services`), Service editing (`PUT /api/v1/services/{id}`), Business settings modification (`PUT /api/v1/settings`), Staff account creation (`POST /api/v1/auth/users`).
  - **Staff operations**: Day-to-day operations including appointment management, waitlist operations, offer creation, cancellation recovery, and metrics reporting.

## Public Customer Capability & Booking Boundaries (Verified)
- **Capability URL Model**: Public customer offer flows (`GET /recovery/offers/{token}` and `POST /recovery/offers/{token}/accept`) use cryptographically random 128-bit UUID tokens (`uuid4`). Tokens serve as capability identifiers that cannot be guessed.
- **Public Booking**: Customers can view active services (`GET /services?active_only=true`), submit bookings (`POST /appointments`), and join waitlists (`POST /waitlist`) without credentials.
- **Rate Limiting**: Sliding-window IP rate limiter protects abuse-prone endpoints:
  - `/api/v1/auth/login`: 10 requests / minute
  - `/api/v1/recovery/offers/{token}/accept`: 20 requests / minute
  - `/api/v1/appointments` & `/api/v1/waitlist`: 30 requests / minute
  - Exceeding quotas returns `HTTP 429 Too Many Requests` with `Retry-After` header.

## Concurrency, Data Integrity & Invariants (Verified)
- **Atomic Acceptance**: `accept_offer` locks both `RecoveryOffer` and `Appointment` using `SELECT ... FOR UPDATE` inside a database transaction to prevent concurrent double-booking.
- **Duplicate Acceptance Guard**: Duplicate acceptance returns `HTTP 400 Bad Request` ("already accepted").
- **Eligibility Validation**: Backend verifies service ID matching, preferred time window bounds, and active waitlist status. Manipulated requests cannot bypass eligibility rules.
- **Bounded Notification Retries**: Email retries are capped at a maximum of 3 attempts. Exceeding attempts returns `HTTP 400 Bad Request`.
- **Test Database Isolation**: Hard safety assertion prevents test runs against the production/dev `/slotback` database.
