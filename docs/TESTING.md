# SlotBack — Testing Strategy

## 1. Purpose

Verify that SlotBack behaves correctly across the frontend, API, PostgreSQL database and deployed environment.

Testing must cover successful workflows, invalid inputs, authorization failures, concurrency, external-service failures and production integration.

This document defines the test contract. Actual results must be recorded separately with execution dates and evidence.

## 2. Testing Stack

| Layer | Tools |
|---|---|
| Backend unit tests | pytest |
| API and integration tests | pytest, HTTPX |
| Database integration | PostgreSQL test database |
| Frontend component tests | Vitest, React Testing Library |
| End-to-end browser tests | Playwright |
| Performance tests | Locust |
| Static quality checks | Ruff, ESLint, TypeScript compiler |
| Coverage | pytest-cov and frontend coverage tooling |

Tests must use isolated test data and must not depend on production records.

## 3. End-to-End Scenarios

### E2E-01: Successful Appointment Booking

**Given:** A customer is authenticated and a valid appointment slot is available.

**When:** The customer selects the service and confirms the appointment.

**Then:**
- The API accepts the valid request.
- Exactly one confirmed appointment is persisted.
- The customer sees the confirmation.
- The appointment appears in the staff dashboard.

### E2E-02: Cancellation and Recovery Offer

**Given:** A confirmed appointment and eligible waitlisted customers exist.

**When:** The customer or authorized staff member cancels the appointment.

**Then:**
- The appointment transitions to the correct cancelled state.
- The slot becomes eligible for recovery.
- An eligible offer is created according to the configured selection rules.
- The notification event is recorded.
- The dashboard reflects the cancellation and offer state.

### E2E-03: Successful Offer Acceptance

**Given:** A customer has an active recovery offer.

**When:** The intended recipient accepts before expiry.

**Then:**
- The backend validates the offer and slot.
- The booking is confirmed atomically.
- The offer transitions to its consumed state.
- The customer receives a confirmation.
- Metrics record the recovery event exactly once.

### E2E-04: Concurrent Acceptance

**Given:** Two requests attempt to claim the same exclusive slot.

**When:** Both acceptance requests execute concurrently.

**Then:**
- At most one request confirms the booking.
- The database contains no duplicate confirmed booking for that slot.
- The losing request receives a meaningful conflict response.
- No duplicate recovery or confirmation event is recorded.

### E2E-05: Expired Offer

**Given:** A recovery offer has expired.

**When:** The customer attempts to accept it.

**Then:**
- The backend rejects the acceptance.
- No confirmed booking is created.
- The expired state remains consistent.
- The frontend displays a clear explanation.

### E2E-06: Authorization and Data Isolation

**Given:** Two customers and a staff account exist.

**When:** A customer attempts to view or modify another customer's booking or offer.

**Then:**
- The backend denies unauthorized access.
- No protected data is disclosed.
- No unauthorized state change occurs.
- The result follows the documented authentication and authorization policy.

### E2E-07: Notification Failure

**Given:** A valid recovery offer exists and the email provider fails.

**When:** Notification delivery is attempted.

**Then:**
- The booking and offer states remain correct.
- The failure is recorded and observable.
- Retry behaviour follows the configured policy.
- Retrying does not create duplicate bookings or notifications beyond the intended delivery semantics.

### E2E-08: Persistence and Deployment

**Given:** The deployed application is connected to PostgreSQL.

**When:** A booking is created and the application is restarted or redeployed.

**Then:**
- The booking remains persisted.
- The API reads the expected database record.
- Frontend and backend health checks succeed.
- Production configuration contains no development database fallback.

## 4. API and Database Tests

Verify:

- Valid and invalid request schemas.
- Authentication and role-based access control.
- Correct HTTP status codes and error responses.
- Database constraints and foreign-key relationships.
- Transaction rollback on failed operations.
- Migration from an empty database to the current schema.
- Idempotency of retried critical operations.
- Timezone and offer-expiry boundary conditions.
- Pagination and filtering behaviour where implemented.

Integration tests must run against PostgreSQL, not SQLite, for features that depend on PostgreSQL-specific constraints, transactions or locking.

## 5. Frontend Tests

Verify:

- Form validation and submission.
- Loading, empty, success and failure states.
- Correct rendering of appointment and offer statuses.
- Expiry and conflict feedback.
- Accessible keyboard navigation and form labels.
- API errors displayed without exposing internal stack traces.
- Responsive behaviour on mobile and desktop viewports.

Component tests complement end-to-end tests; they do not replace them.

## 6. Security and Performance Tests

### Security

Test authorization boundaries, malformed input, SQL injection resistance, secret handling, rate limits on sensitive endpoints and protection against duplicate or replayed requests.

### Performance

Define a reproducible workload and record:

- Concurrent virtual users.
- Request volume and duration.
- p50 and p95 API latency.
- Error rate and throughput.
- Database and application resource usage.

Performance targets must be chosen before the measured run. Do not claim production-scale performance from a local benchmark.

## 7. CI Release Gates

The required pull-request pipeline should execute:

1. Formatting, lint and type checks.
2. Backend unit tests.
3. PostgreSQL integration tests and migrations.
4. Frontend component tests.
5. Critical-path Playwright tests.
6. Production builds.
7. Required security and dependency checks.

A failed required check blocks the release. Deployments should run migrations through a controlled step, followed by smoke tests against the deployed application.

## 8. Evidence and Result Reporting

For each test run, capture:

- Execution date and environment.
- Commit hash or release version.
- Test suite and command.
- Tests passed, failed, skipped and not executed.
- Failure details and root cause.
- Fix or mitigation applied.
- Regression test added, where appropriate.
- Rerun result and supporting CI or report link.

Coverage percentages must include their measurement scope. A passing suite does not establish that every requirement is covered.

## 9. Definition of Test Completion

Testing is complete for a release only when:

- All required critical-path tests pass.
- No known unresolved critical data-integrity or authorization defects remain.
- Database migrations succeed in the release environment.
- The deployed application's critical workflows pass smoke tests.
- Failed tests and skipped tests are disclosed.
- Test evidence is reproducible and linked to the release.

**Reporting rule:** Never replace a failed test result with a successful result from a different run without preserving the original failure. Document what failed, why it failed, what changed and whether the regression test now passes.