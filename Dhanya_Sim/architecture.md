# Fair Drop — Architecture and Web Flow

## 1. Architecture decision

Use a **modular monolith** for the hackathon:

- FastAPI application.
- PostgreSQL as durable source of truth.
- Redis as optional cache/rate-limit/short-lived state.
- Background worker for expiry, lottery, and metrics jobs.
- Separate frontend, simulator, and MediaPipe workspaces.
- HTTP/OpenAPI contracts between workstreams.

Do not begin with multiple microservices. The core challenge is transaction correctness and measurable fairness. A modular monolith keeps those boundaries explicit while reducing operational and merge complexity.

## 2. Component map

```text
Participants / bots
        ↓
Frontend / event page
        ↓
CDN + WAF + API gateway
        ↓
FastAPI application
  ├─ Auth/session module
  ├─ Campaign/status module
  ├─ Admission/permit module
  ├─ Registration/idempotency module
  ├─ Risk/friction/challenge adapter
  ├─ Lottery/roster module
  ├─ Entitlement/claim module
  ├─ Inventory module
  ├─ Metrics/audit module
  └─ Admin module
        ↓
PostgreSQL authority
        ├─ campaigns
        ├─ participants
        ├─ registrations
        ├─ seats
        ├─ entitlements
        ├─ lottery_runs
        └─ audit_events

Redis optional: rate limits, cache, admission metadata
Worker: expiry, draw, standby promotion, aggregation
Simulator: HTTP traffic generator
MediaPipe: challenge engine behind an adapter
```

## 3. Default web flow

### Request entry

Every request enters through TLS, CDN/WAF or edge protection, load balancing, API routing, request ID generation, authentication extraction, schema validation, rate limiting, and structured logging.

### Application

FastAPI routes call domain services. Domain services enforce state transitions and business rules. Repositories perform database reads/writes. External calls have timeouts and explicit failure handling.

### Database

PostgreSQL stores durable business state. Constraints protect rules that must never be violated. Transactions combine related updates. Migrations are versioned.

### Background processing

Slow or retryable work is handled by workers: email, challenge cleanup, expired holds, standby promotion, lottery execution, metrics aggregation, and reconciliation.

## 4. Fair Drop request flow

### A. Join campaign

```text
POST /api/campaigns/{id}/join
```

1. Verify session.
2. Verify campaign exists and is joinable.
3. Apply admission/rate-limit policy.
4. Create a short-lived signed permit bound to session, campaign, operation, expiry, and nonce.
5. Return permit and campaign status.

### B. Register

```text
POST /api/campaigns/{id}/register
```

1. Verify authentication/session.
2. Verify campaign is `OPEN`.
3. Verify admission permit and replay status.
4. Validate request body.
5. Evaluate participant verification and risk state.
6. Check idempotency key and request hash.
7. Insert registration under a transaction.
8. Enforce `unique(campaign_id, participant_id)`.
9. Return durable entry receipt.

### C. Close and freeze

1. Transition `OPEN → CLOSED` using server time.
2. Finalize in-flight requests under the documented cutoff rule.
3. Select eligible registrations.
4. Sort canonical roster.
5. Calculate roster hash.
6. Store policy version/hash.
7. Transition `CLOSED → FROZEN`.

### D. Draw

1. Transition `FROZEN → DRAWING`.
2. Use committed randomness and stored roster hash.
3. Produce deterministic order.
4. First 500 become winners.
5. Next configured set becomes standby.
6. Store `lottery_run` and audit records.
7. Issue short-lived winner entitlements.
8. Transition to `CLAIMING`.

### E. Hold and redeem

```text
POST /api/entitlements/{id}/hold
```

Within a transaction, verify the entitlement, expiry, participant binding, risk state, and available seat; create a hold with expiry.

```text
POST /api/entitlements/{id}/redeem
```

Verify human validation, entitlement, hold ownership, expiry, and seat state; transition `HELD → CONFIRMED` atomically and consume the entitlement.

### F. Expiry and standby

A worker expires stale holds, returns seats to availability, expires old entitlements, promotes the next fixed standby participant, and logs every transition.

## 5. Critical data relationships

```text
campaign 1 ── * participant
campaign 1 ── * registration
participant 1 ── * registration, but only one active registration per campaign
campaign 1 ── * seat
registration 0..1 ── 1 lottery result
winner 1 ── 1 entitlement
entitlement 0..1 ── 1 hold
hold 0..1 ── 1 confirmed allocation
```

## 6. Reliability behavior

### Lost response

The client retries with the same idempotency key. The backend returns the original durable result.

### Database outage

Do not report success without a committed transaction. Return a retryable error and preserve idempotency semantics.

### Redis outage

Degrade cache/rate-limit behavior conservatively. Never use a cache failure as permission to create duplicate ownership.

### Worker restart

Jobs are idempotent and resumable. State transitions are protected by database constraints and transactions.

### Refresh/reconnect

The frontend re-fetches durable server state. It does not create a new registration automatically.

## 7. Cross-team interfaces

```text
Naman → challenge result adapter
Rohan → HTTP/OpenAPI routes and JSON schemas
Dhanya → HTTP APIs and metrics dimensions
Dhruv → database, domain services, security, transactions
```

No contributor imports another contributor’s internal implementation.

## 8. Metrics flow

```text
request logs + domain events + simulator labels
        ↓
metrics aggregation
        ↓
GET /api/campaigns/{id}/metrics
        ↓
operator dashboard / judge evidence
```

Always distinguish raw requests from valid eligible entries when computing fairness.
