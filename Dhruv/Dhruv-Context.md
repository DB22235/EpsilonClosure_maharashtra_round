# Dhruv — Role Context

## Role

You own the **system design and FastAPI backend** for Fair Drop. You are the integration owner for durable state, API contracts, concurrency correctness, allocation integrity, authentication/session behavior, and future challenge/model extensibility.

## Project understanding

Fair Drop must allocate 500 seats among a high-demand population without allowing speed, request volume, repeated attempts, token replay, or queue manipulation to create a meaningful advantage.

The backend must not claim perfect bot detection. It must enforce one eligible entry per participant, freeze the roster, run a reproducible uniform lottery, protect inventory atomically, require human validation before final redemption, and expose evidence through metrics and audit endpoints.

## Primary responsibilities

- Own `/apps/backend`.
- Use Python **3.11.9**.
- Create `/apps/backend/.venv` with Python 3.11.9.
- Design FastAPI modules and dependency boundaries.
- Own PostgreSQL schema and migrations.
- Own authentication, sessions, authorization, and role checks.
- Own campaign/event state machine.
- Own waiting-room/admission permits.
- Own registration, identity uniqueness, and idempotency.
- Own risk orchestration and reason codes.
- Own challenge verification adapter, not MediaPipe internals.
- Own roster freeze and lottery execution.
- Own signed single-use entitlements.
- Own atomic seat holds and confirmation.
- Own replay protection and expiry jobs.
- Own metrics, audit, and public receipt APIs.
- Keep integration boundaries flexible for future models/challenges.

## Do not own & strict boundaries

Do not modify:
- **Rohan’s frontend**: `/apps/frontend/*` (integrate only via HTTP/OpenAPI contracts).
- **Naman’s MediaPipe & Challenge internals**: `/apps/mediapipe/*`, `/apps/backend/app/schemas/challenge.py`, `/apps/backend/app/services/challenge_service.py`, `/apps/backend/app/api/routes_challenges.py`, `turnstile.py`.
- **Dhanya’s simulator**: `/apps/simulator/*` (provide test endpoints and contracts).
- **Database Schema**: `/apps/backend/app/models/*` is **FROZEN**. Do not alter models or generate Alembic migrations.
- **Future modules out of scope for Step 5**: Do not implement lottery, inventory, seat holds, entitlements, or background workers until their respective phases.

Define and document HTTP contracts so the other team members can work independently.

## Current implementation status & Step 5 focus

### Progress to date
- **Step 1 — Scaffold (COMPLETE ✅)**: Clean FastAPI architecture, pydantic-settings, CORS, health endpoints, ruff linted.
- **Step 2 — Database (COMPLETE ✅)**: Async SQLAlchemy 2.0 with asyncpg and NullPool for Supabase transaction pooler (port 6543). All 17 tables created.
- **Step 3 — Auth & JIT Provisioning (COMPLETE ✅)**: JWT decoding, RBAC roles (`PARTICIPANT`, `ADMIN`, etc.), JIT user/profile/participant provisioning.
- **Step 4 — Campaign Lifecycle (COMPLETE ✅)**: Full campaign state machine (`DRAFT` → `COMPLETED`), public status polling, admin management endpoints.
- **Step 4.5 — Integration Test Suite (COMPLETE ✅)**: 18/18 pytest tests passing for health, auth, RBAC, and campaign state machines.
- **Step 4.6 — Live Supabase Auth & ES256 Support (COMPLETE ✅)**: Implemented dual-mode asymmetric ES256 JWKS decoder + HS256 secret fallback with `cryptography`. Verified live user `tester@fairdrop.com`.
- **Step 5 — Registration + Admission Permits (COMPLETE ✅)**: Signed HMAC-SHA256 admission permits, idempotent single registration, challenge seam.
- **Step 7 — Lottery Engine & Roster Freeze (COMPLETE ✅)**: Deterministic uniform lottery with committed randomness and HMAC-SHA256 Fisher-Yates variant.
- **Step 8 — Atomic Seat Holds & Redemption (COMPLETE ✅)**: Row-level locking `SELECT ... FOR UPDATE SKIP LOCKED` for two-phase seat holds and bookings.
- **Steps 9 & 10 — Background Workers, Metrics & Verifiable Audit (COMPLETE ✅)**: Expiry workers, standby promotion, real-time metrics, verifiable audit queries. Full suite: 37/37 tests passing.
- **Step 11 — Rate Limits, Hardening & Production Safety (COMPLETE ✅)**: In-memory sliding window rate limiter, security headers, 64KB body guard, idempotency replay bypass, error sanitization. Full suite: 43/43 tests passing.
- **Files permitted to create/edit**:
  - `app/core/rate_limit_store.py` (NEW)
  - `app/middleware/rate_limit.py` (NEW)
  - `app/middleware/security_headers.py` (NEW)
  - `app/config.py` (add rate limit knobs and body limits)
  - `app/main.py` (mount middleware)
  - `app/dependencies.py` (rate limit dependencies)
  - `app/api/routes_registration.py` (apply limits)
  - `app/api/routes_entitlements.py` (apply limits)
  - `app/api/routes_auth.py` (light limits)
  - `app/api/routes_admin.py` (admin limits)
  - `apps/backend/scripts/test_rate_limits.py` (NEW)
  - `apps/backend/scripts/security_smoke_test.py` (NEW)
  - `apps/backend/scripts/simulate_user_flow.py` (add hardening checks)
  - `apps/backend/tests/test_hardening_and_rate_limits.py` (NEW)
- **Do Not Touch**:
  - Models / Alembic (Schema is **FROZEN**)
  - Naman's files (`/apps/mediapipe/*`, `challenge.py`, `turnstile.py`, etc.)


## Recommended backend structure

```text
/apps/backend/
  app/
    main.py
    config.py
    api/
      routes_campaigns.py
      routes_registration.py
      routes_challenges.py
      routes_entitlements.py
      routes_admin.py
      routes_metrics.py
    domain/
      campaign.py
      registration.py
      lottery.py
      inventory.py
      entitlement.py
      risk.py
    models/
    schemas/
    repositories/
    services/
    workers/
    security/
    integrations/
  migrations/
  tests/
  requirements.txt or pyproject.toml
  README.md
```

Prefer domain/service/repository separation inside one FastAPI deployable application. Do not split into microservices during the hackathon unless there is a compelling existing infrastructure reason.

## Python 3.11.9 setup

```bash
cd /path/to/repository/apps/backend
python3.11 --version   # must be 3.11.9
python3.11 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
```

Pin dependencies. Commit `requirements.txt` or `pyproject.toml` and a lock strategy. Never commit `.venv`.

Suggested baseline packages:

- FastAPI.
- Uvicorn.
- Pydantic v2.
- SQLAlchemy or SQLModel according to team preference.
- Alembic.
- PostgreSQL driver.
- Redis client if Redis is used.
- Pytest and HTTP test client.
- Cryptography/signing library.

Do not add packages without a reason. Keep model/challenge integration behind adapters.

## Data authority

PostgreSQL is the durable source of truth for:

- Campaigns.
- Participants.
- Registrations.
- Lottery runs/results.
- Entitlements.
- Seats/holds/confirmed allocations.
- Audit events.

Redis is optional for:

- Rate-limit counters.
- Cache.
- Short-lived admission metadata.
- Queue metadata.
- Challenge/session acceleration.

A Redis outage must not corrupt durable ownership or create duplicate tickets.

## Core state machines

### Campaign

```text
DRAFT → PREPARING → OPEN → CLOSED → FROZEN → DRAWING → CLAIMING → COMPLETED
```

### Registration

```text
RECEIVED → VALIDATING → ACCEPTED
                         ├─ DUPLICATE
                         ├─ REJECTED
                         └─ QUARANTINED
```

### Entitlement/claim

```text
SELECTED → CLAIM_PENDING → HELD → CONFIRMED
                    └──────→ EXPIRED
```

### Seat

```text
AVAILABLE → HELD → CONFIRMED
      ↑       └──→ AVAILABLE after expiry/release
```

Reject operations that are invalid for the current state.

## API contract

Implement and document:

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
POST /api/admin/campaigns/{id}/draw
POST /api/admin/campaigns/{id}/pause
```

Each state-changing endpoint must define:

- Authentication.
- Authorization.
- Request schema.
- Response schema.
- Idempotency behavior.
- State transition rules.
- Error codes.
- Rate-limit class.
- Audit event.

Standard error response:

```json
{
  "error": {
    "code": "REGISTRATION_CLOSED",
    "message": "Registration has ended",
    "request_id": "req_123"
  }
}
```

Expose OpenAPI and keep frontend/simulator consumption based on this contract.

## Registration and idempotency

Registration must be transactional and idempotent.

Required uniqueness:

```text
unique(campaign_id, participant_id)
unique(campaign_id, idempotency_key)
```

Store:

- Idempotency scope.
- Key.
- Request hash.
- Result status/reference.
- Expiry.

Behavior:

```text
same key + same request       → original result
same key + different request  → reject conflict
new key + existing participant→ existing/duplicate policy result
```

If the network fails after a successful commit, a retry must recover the original result rather than create a new entry.

## Admission permits and replay protection

A signed permit represents:

- Campaign ID.
- Participant/session ID.
- Expiry.
- Nonce.
- Allowed operation.
- Server signature.

Verify signature, expiration, session binding, operation binding, and nonce replay status.

A queue number shown in the browser is not authorization.

Winner entitlements are short-lived and single-use. Store a nonce hash or equivalent replay record. Expired or redeemed entitlements must fail consistently.

## Challenge integration

Naman owns MediaPipe internals. Create a backend challenge adapter that can accept:

- Turnstile result.
- MediaPipe result.
- Visual challenge result.
- Mock challenge result for testing.

The backend validates:

- Challenge exists.
- Challenge belongs to session/campaign.
- Nonce matches.
- Challenge is not expired.
- Attempt limit is not exceeded.
- Challenge is not already consumed.
- Result is structurally valid.

Do not treat challenge success as proof of unique human identity. Treat it as one risk/friction signal.

## Risk and friction

Implement a transparent MVP score and reason codes. Example signals:

```text
RATE_BURST
MULTI_SESSION
REPLAY_ATTEMPT
DUPLICATE_ENTRY
CHALLENGE_FAILURE
EXPIRED_HOLD
SUSPICIOUS_TRANSITION
```

Recommended thresholds:

```text
0–29 LOW      normal flow
30–59 MEDIUM  slow down or require step-up challenge
60+ HIGH      challenge, cooldown, quarantine, or block operation
```

Do not permanently classify users from one shared IP, one refresh, slow network, unusual browser, assistive technology, or keyboard-only behavior.

## Roster freeze and lottery

At cutoff:

1. Transition `OPEN → CLOSED`.
2. Complete/reject in-flight entries by a documented server-time rule.
3. Select valid eligible entries.
4. Apply duplicate rule.
5. Sort canonical roster.
6. Calculate roster hash.
7. Store policy version/hash.
8. Transition `CLOSED → FROZEN`.

Draw once:

1. Use committed randomness.
2. Include campaign ID, roster hash, policy/algorithm version.
3. Produce deterministic winner and standby ordering.
4. Store `lottery_run` audit record.
5. Create winner entitlements.
6. Transition `DRAWING → CLAIMING`.

The public result should be replayable from stored audit metadata without exposing personal data.

## Atomic inventory and claims

The authoritative operation must prevent overselling under concurrent requests.

A hold transaction should:

```text
BEGIN
lock or atomically claim a valid entitlement
verify entitlement state and expiry
lock an available seat or decrement safe inventory
create the hold
store hold expiry
COMMIT
```

A confirm transaction should:

```text
BEGIN
lock hold
verify human validation and expiry
verify seat belongs to this hold
transition HELD → CONFIRMED
consume entitlement
COMMIT
```

Do not hold database transactions open while calling slow external services. Store intermediate state, perform the call, then transition safely.

## Timers

Server-authoritative timers:

- Idle session: recommended 2 minutes.
- Absolute redemption session: recommended 5 minutes.
- Seat hold: recommended 90–120 seconds.

Expiry workers must release expired holds and invalidate old entitlements. Client timers are display aids only.

## Metrics and audit APIs

Metrics must be real, not hard-coded. Expose:

- Total attempts.
- Unique participants.
- Eligible entries.
- Duplicate attempts.
- Suspicious traffic.
- Winners/standby.
- Selection rate by client class.
- Bot advantage ratio.
- Available/held/confirmed seats.
- Expired holds.
- Oversell count.
- Duplicate allocation count.
- P95/P99 latency.
- Error/retry rate.
- Challenge success/failure/abandonment.
- Cooldowns.
- False positives.

Public audit may expose:

- Campaign ID.
- Policy version.
- Registration cutoff.
- Registered/eligible counts.
- Duplicate count.
- Roster hash.
- Randomness reference.
- Algorithm version.
- Winner count.
- Standby rule.
- Aggregate rates.
- Oversell and duplicate-allocation counts.

Private fairness receipt may expose participant-specific result and audit references.

## Required invariants and tests

```text
confirmed_seats <= campaign_capacity
one seat cannot belong to two participants
one participant cannot exceed ticket limit
one campaign + one verified participant = one registration
expired holds do not remain unavailable
replayed permits/challenges/entitlements are rejected
same idempotency key + same request = same result
same idempotency key + different request = rejection
```

Test:

- Parallel registration.
- Parallel hold.
- Parallel redeem.
- Lost response and retry.
- Worker restart.
- Database conflict.
- Expired holds.
- Roster freeze boundary.
- Draw replay.
- Token replay.
- Shared-network users.
- Slow users.

## Integration with the team

### Naman

Provide a challenge adapter. Do not import his MediaPipe internals. Agree on result fields: challenge ID, session, campaign, type, nonce, result, confidence, attempt, expiry, implementation version.

### Rohan

Provide OpenAPI schemas, stable error codes, timer/status endpoints, and example JSON responses. Do not require frontend access to database or internal services.

### Dhanya

Provide documented HTTP endpoints and test fixtures. Expose metrics sufficient to compare valid entries and winners by simulator class. Do not add test-only bypasses to production logic without clear environment controls.

## Definition of done

- Clean FastAPI startup from Python 3.11.9 venv.
- Migrations create the required schema.
- Campaign lifecycle works.
- Registration is idempotent and unique.
- Roster freezes before draw.
- Lottery is deterministic/reproducible.
- Standby order is fixed.
- Entitlements are signed/bound/expiring/single-use.
- Holds and confirmations are atomic.
- Parallel requests cannot oversell.
- Refresh/reconnect retrieves durable state.
- Challenge adapter supports MediaPipe/Turnstile/mock modes.
- Replay and conflict errors are explicit.
- Metrics and audit APIs return real data.
- Backend remains modular for future model/challenge integration.
- Work remains inside `/apps/backend` and agreed shared API contracts.
