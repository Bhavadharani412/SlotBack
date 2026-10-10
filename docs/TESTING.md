# SlotBack — Testing

## Layers
- Unit: pytest for business rules and metric calculations.
- API: HTTPX for status codes, schemas, authentication and authorization.
- Integration: PostgreSQL-backed tests for transactions, constraints and migrations.
- Frontend: Vitest/React Testing Library after UI integration.
- E2E: Playwright for booking → cancellation → offer → acceptance → confirmed booking.
- Performance: Locust when workload and targets have been defined.

## Critical scenarios
1. Valid booking persists once.
2. Invalid or unavailable slot is rejected.
3. Cancellation releases capacity and triggers eligible recovery.
4. Active offer acceptance confirms at most one booking.
5. Expired/consumed offer is rejected.
6. Cross-customer access is denied.
7. Notification failure is visible and recoverable.
8. Data persists across restart/redeployment.
9. Deployed frontend, API and PostgreSQL integration pass smoke checks.

## Reporting
Record date, commit, environment, command, passed/failed/skipped counts, failures, root cause, fix and regression test. Never claim unexecuted tests passed. Coverage scope and skipped tests must be disclosed.
