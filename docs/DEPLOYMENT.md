# SlotBack — Hardened Production Deployment & Operations Guide

## Overview

SlotBack uses a single-process architecture where FastAPI serves both REST API endpoints and static SPA assets (`frontend/dist`) with PostgreSQL as the persistent authoritative store.

---

## 1. Environment Configurations

All environment variables must be declared prior to starting the production instance.

| Variable | Description | Production Requirement |
|---|---|---|
| `APP_NAME` | Service identifier | e.g. `SlotBack API` |
| `APP_ENV` | Environment identifier | Must be `production` |
| `DEBUG` | FastAPI debug mode | Must be `false` (enforced at startup) |
| `SECRET_KEY` | JWT HMAC-SHA256 signing secret | Minimum 32 characters, high-entropy random string |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://<user>:<pass>@<host>:5432/<db>` |
| `CORS_ORIGINS` | Permitted browser origins | Explicit URLs (e.g. `https://slotback.example.com`). Wildcards forbidden. |
| `LOG_LEVEL` | Logging verbosity | `INFO` or `WARNING` |
| `SMTP_HOST` | Outbound mail server | Optional (falls back to structured dev logs if empty) |
| `SMTP_PORT` | SMTP port | Typically `587` (TLS) or `465` (SSL) |
| `SMTP_USER` | SMTP username | Account credential |
| `SMTP_PASSWORD`| SMTP password | Account credential |
| `SMTP_FROM` | Sender email address | e.g. `notifications@slotback.example.com` |

---

## 2. Reproducible Production Build

### Step 1: Build Frontend SPA
```bash
# In frontend directory
pnpm install --frozen-lockfile
pnpm build
```
This generates the optimized bundle in `frontend/dist`.

### Step 2: Install Backend Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run Database Migrations
Always run database migrations as a dedicated release phase before routing user traffic:
```bash
alembic upgrade head
```

### Step 4: Start Production Server
Run Uvicorn with standard production process management (e.g. Systemd, Docker, or Kubernetes):
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips='*'
```

---

## 3. Health & Readiness Probes

SlotBack separates liveness and readiness probes to prevent traffic routing during outages or cold starts:

- **Liveness Probe (`GET /health/live` or `/health`)**:
  - Tests process availability and event loop responsiveness.
  - Returns `HTTP 200 {"status": "ok", "service": "slotback-api"}`.
  - Recommended configuration: period 10s, timeout 2s, failure threshold 3.

- **Readiness Probe (`GET /health/ready`)**:
  - Validates active PostgreSQL database connectivity (`SELECT 1`).
  - Returns `HTTP 200 {"status": "ready", "database": "connected"}` if healthy.
  - Returns `HTTP 503 {"status": "unavailable", "database": "disconnected"}` if database is unreachable.
  - Recommended configuration: period 5s, timeout 3s, failure threshold 2.

---

## 4. Least-Privilege Database Permissions

To prevent privilege escalation, the application should connect with a role that has only DML/DDL permissions on the `slotback` schema, and never superuser privileges:

```sql
-- Create application user
CREATE USER slotback WITH PASSWORD 'STRONG_PRODUCTION_PASSWORD' NOSUPERUSER CREATEDB;

-- Grant permissions to database
GRANT CONNECT ON DATABASE slotback TO slotback;
GRANT USAGE, CREATE ON SCHEMA public TO slotback;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO slotback;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO slotback;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO slotback;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO slotback;
```

---

## 5. Database Backup and Restore Procedures

### Automated Daily Backup (`pg_dump`)
```bash
# Run logical backup with custom compressed format
pg_dump -h <DB_HOST> -U slotback -d slotback -Fc -f "/var/backups/slotback_$(date +%Y%m%d_%H%M%S).dump"
```

### Point-in-Time Restore (`pg_restore`)
```bash
# Restore backup to a clean database
pg_restore -h <DB_HOST> -U slotback -d slotback --clean --if-exists -v "/var/backups/slotback_<TIMESTAMP>.dump"
```

---

## 6. Deployment & Rollback Sequence

1. **Pre-deployment Verification**:
   - Verify all tests pass in CI (`pytest -ra -v`, Playwright E2E suite, TypeScript typecheck).
2. **Execute Backward-Compatible Migration**:
   - Run `alembic upgrade head`. Schema additions must maintain backward compatibility with currently running pods/processes.
3. **Deploy Application Artifact**:
   - Deploy new container/build.
   - Wait for `/health/ready` to report `ready`.
4. **Traffic Promotion**:
   - Switch load balancer or rollout ingress to new version.
5. **Rollback Procedure**:
   - If `/health/ready` fails or error rates increase, rollback traffic to the previous application artifact.
   - If schema downgrade is necessary and safe: `alembic downgrade -1`.
