# SlotBack — AI Agent Engineering Rules

## Mission
Build SlotBack, a reliable appointment cancellation-recovery product for small service businesses. Help staff recover released appointment capacity through eligible waitlist offers, safe acceptance, clear status and measurable outcomes.

## Read before work
1. `CHANGELOG.md` for current project state, decisions and next actions.
2. `docs/PROJECT_OVERVIEW.md` for product scope.
3. `docs/ARCHITECTURE.md` for architecture and invariants.
4. `docs/TESTING.md` for acceptance and verification rules.
5. `docs/METRICS.md` and `docs/DEPLOYMENT.md` when relevant.

## Non-negotiable rules
- Inspect existing code and tests before editing. Do not overwrite working code blindly.
- Preserve the product name SlotBack and established API contracts unless a documented decision changes them.
- Do not invent test results, coverage, deployment status, user activity, business outcomes or performance measurements.
- Never claim a command passed unless you ran it and inspected its result.
- Use PostgreSQL as the authoritative data store. Do not silently fall back to SQLite.
- Keep secrets out of source control. Use environment variables and `.env.example` with placeholders only.
- Keep business rules in service-layer code; API handlers should remain thin.
- Validate all inputs on the backend. Frontend validation is not a security boundary.
- Enforce authorization server-side for every protected resource.
- Treat concurrency and database integrity as core requirements, not frontend concerns.
- Use migrations for schema changes; do not rely on manual production schema edits.
- Add or update tests for every behavior change and regression.
- Prefer small, reviewable changes over broad rewrites.
- Update `CHANGELOG.md` after meaningful work with completed changes, actual verification, failures, fixes and remaining work.
- Keep documents concise and consistent; do not duplicate full documentation in the changelog.
- Never include real personal data, production secrets or sensitive logs in examples or test fixtures.

## Backend conventions
- Python 3.12+.
- FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic and PostgreSQL via psycopg 3.
- Use type hints and explicit schemas.
- Use UTC for persisted timestamps.
- Use transactions for related state changes.
- Handle repeated requests safely for critical operations.
- Do not send email while holding database locks.
- Add structured logs without credentials, tokens or sensitive customer data.
- Use a separate PostgreSQL database for tests.

## Verification protocol
Before saying work is complete:
1. List files changed and why.
2. Run relevant format/lint/type/test/build commands.
3. Report exact commands and real outcomes, including failures and skipped tests.
4. If a check cannot run, state why; do not imply it passed.
5. Record known limitations and next steps.

## Current frontend boundary
Stitch is generating the UI separately. Do not scaffold or replace the React frontend until its output is ready. Backend API contracts should remain frontend-independent and documented through OpenAPI.
