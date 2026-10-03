# Dhanya — Role Context

## Role

You own **AI/adversarial simulation testing** for Fair Drop. Your job is to create configurable simulated clients that pressure the HTTP system, test fairness and integrity invariants, and produce evidence for the judges.

## Project understanding

Fair Drop must show that automated traffic cannot gain a meaningful allocation advantage merely by sending more requests, acting faster, retrying, replaying tokens, or racing for the same seat.

You are not building a bot detector. You are building the adversarial test environment that demonstrates whether the backend actually resists those behaviors.

## Primary responsibilities

- Own `/apps/simulator` and `/tests/simulation`.
- Implement configurable client profiles.
- Generate normal and adversarial traffic against documented HTTP APIs.
- Never import Dhruv’s backend internals or connect directly to PostgreSQL for ordinary tests.
- Create reproducible scenarios with fixed seeds/configuration.
- Measure request outcomes, fairness, latency, error rate, duplicate prevention, and inventory integrity.
- Generate machine-readable JSON/CSV results.
- Generate dashboard-ready aggregate metrics.
- Produce attack reports for the demo.
- Test failure and recovery behavior.

## Recommended directory ownership

```text
/apps/simulator/
  README.md
  profiles/
  scenarios/
  runner.py or runner.ts
  metrics/
  configs/
/tests/simulation/
  reports/
  fixtures/
```

If you use Python, do not require Naman’s or Dhruv’s virtual environment. Keep simulator dependencies separate. The simulator may use Python or Node based on the strongest team preference; its contract is HTTP.

## Required simulated client profiles

### Normal human

- One account.
- Low request rate.
- Follows the ordinary flow.
- May refresh once.
- May reconnect.
- May take longer to complete a challenge.

### Fast bot

- Sends registration requests immediately.
- Tries to win through speed.
- Does not necessarily send huge volume.

### Burst bot

- Sends many parallel requests in a short interval.
- Reuses the same identity where configured.

### Retry bot

- Repeats requests after timeouts or lost responses.
- Tests idempotency and uncertain-result recovery.

### Account farm

- Uses many accounts.
- Tests duplicate identity relationships and one-entry rules.

### Direct API bot

- Skips the frontend.
- Calls protected endpoints directly.
- Tests that the backend, not the UI, enforces controls.

### Token replay attacker

- Reuses admission permits, challenge nonces, or winner entitlements.
- Tests expiry, binding, and single-use behavior.

### Race-condition attacker

- Sends parallel hold/redeem requests.
- Targets the same entitlement or seat.
- Must never create duplicate ownership or oversell.

### Legitimate shared-network user

- Many distinct participants share one IP.
- Tests that IP-only blocking does not reject legitimate users.

### Slow/accessibility user

- Higher latency.
- Slower interaction.
- Keyboard-only or challenge fallback behavior.
- Tests false positives and unfair friction.

## Configurable dimensions

Every scenario should allow configuration of:

- Number of clients.
- Client profile.
- Request rate.
- Concurrency.
- Timing jitter.
- Number of accounts.
- IP diversity.
- Retry count and backoff.
- Challenge behavior.
- Event capacity.
- Population size.
- Failure injection rate.
- Registration-window timing.

Use a deterministic seed so a result can be reproduced.

## Required test scenarios

1. Normal registration with no abuse.
2. High-volume duplicate requests from one identity.
3. Distributed moderate-volume bots.
4. Retry after lost response.
5. Direct API access without frontend flow.
6. Admission-token replay.
7. Challenge replay.
8. Entitlement replay.
9. Two clients racing for the same seat.
10. Hold expiry and standby promotion.
11. Database/cache temporary failure if the harness supports it.
12. Shared IP with many legitimate users.
13. Slow users versus fast bots.
14. Mixed population: normal users plus all attack classes.
15. Registration cutoff boundary.

## Metrics to produce

### Participation

- Total requests.
- Unique participants.
- Valid registrations.
- Duplicate attempts.
- Rejected attempts.
- Quarantined attempts.
- Cooldowns.
- Challenge requests and outcomes.

### Fairness

- Winners by client class.
- Valid entries by client class.
- Selection rate by client class.
- Expected selection probability.
- Absolute winner-rate difference.
- Bot advantage ratio.
- Confidence intervals where practical.
- Selection rate after controlling for valid entries.

Do not compare raw bot request count directly with human winner count. Compare winners to **valid eligible entries**.

### Integrity

- Confirmed seats.
- Available/held/confirmed counts.
- Oversell count.
- Duplicate allocation count.
- Duplicate registration count.
- Negative inventory occurrences.
- Replay rejection count.
- Idempotency consistency.
- Expired holds released.
- Standby promotions.

Expected critical results:

```text
confirmed_seats <= capacity
oversell_count = 0
duplicate_allocation_count = 0
replay_success_count = 0
```

### Reliability

- Throughput.
- P50/P95/P99 latency.
- Error rate.
- Timeout rate.
- Retry rate.
- Queue/admission depth.
- Recovery success rate.
- Challenge abandonment.
- False-positive count for shared-network and slow users.

## Fairness interpretation

A bot can be selected if it has one valid entry. Do not report that as a failure by itself.

The key question is:

> Did extra traffic create extra valid entries or higher selection probability after controlling for valid entries?

The strongest demo result is:

```text
Bots generated most of the requests,
but did not obtain a proportional allocation advantage.
```

Do not hard-code results. The frontend dashboard must read actual generated metrics.

## API usage rules

Use documented HTTP endpoints only:

```text
POST /api/campaigns/{id}/join
GET  /api/campaigns/{id}/status
POST /api/campaigns/{id}/register
POST /api/challenges
POST /api/challenges/{id}/verify
GET  /api/campaigns/{id}/result
POST /api/entitlements/{id}/hold
POST /api/entitlements/{id}/redeem
POST /api/entitlements/{id}/release
GET  /api/campaigns/{id}/audit
GET  /api/campaigns/{id}/metrics
```

Record:

- Request ID.
- Client class.
- Identity ID.
- Idempotency key.
- Status code.
- Error code.
- Start/end time.
- Retry number.
- Outcome.

Do not bypass the API by writing directly to the database. Direct database manipulation cannot prove that production behavior is correct.

## Report format

Every attack report should include:

```text
Scenario name
Configuration
Population by client type
Total requests
Valid entries
Winners
Selection rates
Latency percentiles
Error/retry counts
Integrity invariant results
Interpretation
Limitations
```

Include raw JSON/CSV output so claims can be verified.

## Integration with Dhruv

Request stable error codes and metric dimensions from Dhruv. Report missing or ambiguous behavior as a contract issue rather than patching backend assumptions into the simulator.

The backend must expose enough information for testing without exposing sensitive private data. Prefer a demo/admin metrics endpoint or test-only fixtures rather than returning secrets.

## Integration with Rohan

Provide the frontend with metric names and JSON examples. Rohan should render the results from the backend or a stored report, not re-calculate or invent them in the browser.

## Integration with Naman

Use mock challenge responses for load testing. Separate:

- A realistic challenge-flow test.
- A large-scale HTTP load test that should not require 50,000 real cameras.

Test replay, timeout, failure, and fallback behavior using deterministic fixtures.

## Definition of done

- All required client profiles exist.
- Scenarios are reproducible.
- Metrics distinguish raw requests from valid entries.
- Race tests show zero overselling and zero duplicate allocations.
- Replay tests show rejection.
- Retry tests show idempotent results.
- Shared-network and slow-user scenarios measure false positives.
- Reports are generated from actual runs.
- Simulator remains independent of backend internals and other team directories.
