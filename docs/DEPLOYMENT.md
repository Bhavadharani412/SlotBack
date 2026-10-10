# SlotBack — Deployment and CI

## Environments
Maintain separate local, test/staging and production configuration. Use managed PostgreSQL with restricted credentials. Never commit `.env` or real secrets.

## Local setup
1. Install Python 3.12+.
2. Create and activate a virtual environment.
3. Install `requirements-dev.txt`.
4. Create a PostgreSQL database and configure `.env` using `.env.example`.
5. Run the API with `uvicorn backend.app.main:app --reload`.
6. Verify `/health` and `/docs`.

## CI gates
- Ruff lint checks.
- pytest unit and integration tests against PostgreSQL.
- Type checks where configured.
- Frontend lint, type checks, component tests and build after frontend integration.
- Playwright critical-path E2E tests when a test environment is available.
- Dependency/security checks.
- Required checks must pass before merge/release.

## Release sequence
1. Build an immutable artifact.
2. Verify required CI checks.
3. Apply backward-compatible database migrations as a controlled step.
4. Deploy the API and frontend.
5. Run health and critical-path smoke tests.
6. Confirm logs, database connectivity and configuration.
7. If unhealthy, stop promotion and follow the documented rollback/recovery procedure.

## Evidence
Record commit/release identifier, deployment environment, migration outcome, smoke-test result, timestamp and known limitations. Never report a deployment as successful without checking the deployed service.
