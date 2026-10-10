# SlotBack — Metrics and OKRs

## Rules
- Record baseline, target, actual, period, sample size, source/query and limitations.
- Separate proposed targets from measured results.
- Never invent results or infer revenue impact without evidence.
- Preserve failed runs and document the fix and regression evidence.
- Metrics must be reproducible from persisted data or recorded test artifacts.

## Product metrics
| Metric | Definition |
|---|---|
| Eligible cancellations | Cancelled appointments meeting the recovery eligibility rules in the reporting period |
| Recovered completed appointments | Distinct appointments originating from recovery offers and subsequently completed |
| Recovery rate | Recovered eligible slots / eligible cancelled slots × 100; disclose the exact counting rules |
| Time to refill | Time from eligible cancellation to confirmed replacement booking; report median and sample size |
| Notification failure rate | Failed delivery attempts / total delivery attempts; define retry counting |
| Staff effort | Measured staff minutes per comparable recovery workflow, with method and sample size |

## Engineering metrics
- Critical-path E2E pass rate = passed critical-path tests / executed critical-path tests.
- Test coverage: report line and branch coverage separately, including scope.
- API latency: p50/p95, request count, workload, environment and date.
- Error rate: failed requests / total requests, with excluded health checks disclosed.
- CI reliability: successful required runs / completed required runs in a stated period.

## OKR tracking
For every objective, record key result, baseline, target, actual, status, measurement method, evidence link, period and next action. A target is not an achieved result.
