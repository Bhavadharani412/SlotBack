# SlotBack — Architecture

## Shape
React + TypeScript frontend (integrated after Stitch) → FastAPI REST API → service layer → SQLAlchemy → PostgreSQL. Alembic manages schema migrations. GitHub Actions runs quality gates.

## Backend layers
- `api/`: routing, request/response schemas and HTTP concerns.
- `services/`: business rules and workflows.
- `repositories/`: database access when abstraction is useful.
- `models/`: SQLAlchemy persistence models.
- `schemas/`: Pydantic API contracts.
- `core/`: configuration, security and logging.
- `db/`: engine, session and declarative base.

## Invariants
- No slot can be confirmed twice.
- Offer expiry and eligibility are checked server-side at acceptance.
- Customer authorization is enforced on every protected resource.
- Related state changes use database transactions.
- Notifications are not sent while holding database locks.
- Metrics derive from persisted records and documented definitions.

## Database
Use PostgreSQL in development, tests and production. Use UTC timestamps, foreign keys, constraints, indexes and versioned migrations. Do not silently fall back to SQLite.

## API
Use `/api/v1`, consistent error responses, validated schemas and FastAPI-generated OpenAPI docs. Keep API handlers thin and business rules in services.
