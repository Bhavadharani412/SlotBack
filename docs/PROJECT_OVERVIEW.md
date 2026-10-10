# SlotBack — Project Overview

## 1. Problem Statement

Small service businesses such as salons, tutoring centres and repair shops lose appointment capacity when customers cancel or fail to attend. Meanwhile, other customers may be waiting for suitable appointments.

Without a structured recovery workflow, staff must manually contact customers, track availability and coordinate replacements. This creates operational overhead and makes it difficult to measure how much appointment capacity is recovered.

## 2. How We Solve It

SlotBack is a web application that helps service businesses recover cancelled appointment slots by matching them with eligible waitlisted customers.

The system allows businesses to manage appointments, process cancellations, offer released slots to eligible customers and track recovery outcomes.

### Core Workflow

1. Staff configure services and appointment availability.
2. Customers book appointments or join a waitlist.
3. When an appointment is cancelled, the system identifies eligible waitlisted customers.
4. The system issues a time-limited offer and notifies the customer.
5. The customer accepts the offer, and the system confirms the booking safely.
6. The dashboard records the outcome and updates business metrics.

## 3. Product Scope

### Initial Release

- Role-based authentication and authorization.
- Service and availability management.
- Appointment booking, cancellation and rescheduling.
- Customer waitlist management.
- Cancellation recovery and expiring offers.
- Email notifications with failure tracking.
- Appointment and recovery dashboard.
- API documentation and automated testing.

### Out of Scope for the Initial Release

- AI-based appointment recommendations.
- Native mobile applications.
- Payment processing.
- Multi-branch enterprise management.
- Guaranteed revenue recovery.

## 4. Technology Stack

- **Frontend:** React, TypeScript and Vite.
- **UI:** Responsive, accessible component-based design.
- **Backend:** Python and FastAPI.
- **Database:** PostgreSQL.
- **ORM and migrations:** SQLAlchemy and Alembic.
- **Testing:** pytest, HTTPX, React Testing Library and Playwright.
- **CI/CD:** GitHub Actions.
- **Deployment:** Independently deployed frontend and backend with managed PostgreSQL.

## 5. Success Measurement

Success will be evaluated using actual application and pilot data.

- Number of eligible cancelled appointments.
- Number of recovered appointments subsequently completed.
- Recovery rate and time to refill.
- Staff effort per recovered appointment.
- Duplicate booking attempts and invariant violations.
- Critical-path end-to-end test results.
- Production API latency and error rate.

Each metric must have a documented definition, measurement period, data source and calculation. Targets are hypotheses until validated. No business impact or testing result is considered achieved without supporting evidence.

## 6. Definition of Done

The initial release is complete when:

- The core booking and recovery workflow works end to end.
- PostgreSQL enforces the required data integrity constraints.
- Concurrent requests cannot create duplicate confirmed bookings.
- Critical user journeys pass automated end-to-end tests.
- Required CI checks pass before release.
- The application is deployed and verified through production smoke tests.
- Architecture, testing and deployment instructions are reproducible.

**Product principle:** Build a reliable appointment recovery workflow first. Add complexity only when real user needs or measured results justify it.