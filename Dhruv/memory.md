# Fair Drop — Project Memory

> Living project memory. Update this file after meaningful decisions, implementation milestones, test runs, and integration changes.

## 1. Project identity

- Project: Fair Drop.
- Challenge: Sell/allocate 500 seats to up to 50,000 participants without letting speed, request volume, or repeated automation create a meaningful advantage.
- Team: Naman, Rohan, Dhanya, Dhruv.
- Backend direction: FastAPI with Python 3.11.9 for Dhruv.
- MediaPipe direction: Python 3.11.9 for Naman.
- Core architecture: modular monolith, PostgreSQL authority, optional Redis, background workers, HTTP contracts.

## 2. Decisions already made

1. Do not claim perfect bot detection.
2. Remove the speed race with registration plus a frozen uniform lottery.
3. One verified participant per campaign gets one eligible entry.
4. Repeated requests do not become extra lottery chances.
5. Admission protects capacity; it does not secretly decide winners.
6. PostgreSQL is the durable source of truth for registrations, seats, holds, entitlements, and audit records.
7. Redis is optional fast state and never the only durable inventory authority.
8. Human validation is required before final redemption.
9. Challenges are risk/friction signals, not proof of humanity.
10. Inventory must be protected with atomic transactions.
11. Entitlements and permits are short-lived, bound, and replay-protected.
12. Metrics must be generated from actual simulations.
13. Use a modular monolith before considering microservices.
14. Workspaces are separated to avoid merge conflicts.

## 3. Team ownership

```text
Naman  → /apps/mediapipe   → MediaPipe challenges and challenge contract
Rohan  → /apps/frontend    → frontend and HTTP integration
Dhanya → /apps/simulator   → adversarial simulation and evidence
Dhruv  → /apps/backend     → FastAPI, database, allocation, inventory, contracts
```

Shared contract:

```text
/packages/api-contract → Dhruv defines; all consume
```

## 4. Documents created

- `FairDrop-Universal-Context.md` — universal team context.
- `Naman-Context.md` — MediaPipe role context.
- `Rohan-Context.md` — frontend role context.
- `Dhanya-Context.md` — simulator/testing role context.
- `Dhruv-Context.md` — backend/system-design role context.
- `FairDrop-Team-Workflow.md` — merge-conflict and collaboration rules.
- `fair-drop-system-design.md` — production backend foundation and Fair Drop-specific design.
- `prd.md` — product requirements.
- `architecture.md` — architecture and web flow.
- `rules.md` — engineering rules and library policy.
- `phases.md` — eight implementation phases.
- `design.md` — visual system.
- `memory.md` — this living record.
- `Fair Drop — Master Backend and Frontend Integration Guide.md` — **DEFINITIVE CONTRACT** (2184 lines). Read in full. Covers: 15 non-negotiable decisions, end-to-end lifecycle, role/auth model (Supabase+FastAPI), campaign state machine (8 states), registration state machine, waiting room/permits, participants/sessions model, risk scoring (8 signals, 3 levels), challenge adapter architecture, roster freeze + lottery process, entitlement state machine, atomic inventory (hold + confirm transactions), idempotency table + behavior, complete API route contract (sections 14.1–14.7), standard response/error envelope, Next.js integration rules, frontend route map, timer/recovery/polling patterns, error code→frontend behavior mapping, full DB schema summary (16 tables), FastAPI module structure, configuration/secrets, Redis behavior, 4 background workers, security+privacy requirements, full test plan (unit/integration/concurrency/adversarial), metrics/fairness evidence definitions, frontend page↔backend state mapping table, admin frontend flow, team contract rules, 21-step judge demo sequence, and the definition of done (29 criteria).

## 5. Current status

### Completed in planning/context

- Problem statement read and clarified.
- Coldplay/BookMyShow incident researched as a real-world motivation.
- Fairness principle selected: remove the race; do not promise perfect bot detection.
- Backend system design drafted.
- User walkthrough drafted.
- Universal and role-specific context files created.
- Ownership and merge-conflict boundaries defined.
- PRD, architecture, rules, phases, design, and memory files created.

### Step 1 — Scaffold (COMPLETE ✅)

**Supabase project URL confirmed:** `https://gjbijluacysjudkvpivd.supabase.co`
**Plan artifact:** `step1_implementation_plan.md`

- All 17 scaffold files created strictly within `/apps/backend/`.
- Fast, clean startup; health check endpoints verified; linted with ruff (0 errors).

### Step 2 — Database & Foundation Models (COMPLETE ✅)

**Plan artifact:** `step2_implementation_plan.md`

- Dependencies added: `asyncpg==0.30.0`, `SQLAlchemy[asyncio]==2.0.36`, `alembic==1.14.0`.
- Configured async SQLAlchemy 2.0 engine in `app/db/session.py` with `NullPool` for compatibility with Supabase's transaction pooler on port 6543 (`aws-0-ap-south-1.pooler.supabase.com:6543/postgres`).
- All 17 core database tables initialized directly in Supabase PostgreSQL:
  1. `profiles`
  2. `participants`
  3. `campaigns`
  4. `sessions`
  5. `admission_permits`
  6. `registrations`
  7. `challenges`
  8. `lottery_runs`
  9. `lottery_entries`
  10. `entitlements`
  11. `seats`
  12. `holds`
  13. `allocations`
  14. `idempotency_records`
  15. `audit_events`
  16. `system_metrics`
  17. `rate_limit_buckets`
- Database schema is **FROZEN**. No further migrations or DDL alterations.
- Database readiness ping wired into `GET /health` (`status: healthy`, `db: connected`).

### Step 3 — Auth, RBAC & JIT Participant Provisioning (COMPLETE ✅)

**Plan artifact:** `step3_implementation_plan.md`

- Implemented token decoding and signature verification in `app/security/jwt.py`.
- Auth dependencies created in `app/security/dependencies.py`:
  - `get_current_identity`: extracts JWT payload, user ID, role, and claims.
  - `require_role(...)`: enforces RBAC roles (`PARTICIPANT`, `ADMIN`, `OPERATOR`, `AUDITOR`).
  - `get_current_participant`: retrieves or JIT-provisions participant record.
  - `require_verified_participant`: ensures participant verification before critical actions.
- Built Just-In-Time (JIT) provisioning in `app/services/auth_service.py`: automatically syncs Supabase `auth.users` to `profiles` and `participants` rows upon first authenticated request.
- Endpoints created in `app/api/routes_auth.py`:
  - `GET /api/v1/auth/me`: returns authenticated identity, profile, and participant state.
  - `POST /api/v1/auth/refresh`: token refresh endpoint.

### Step 4 — Campaign Lifecycle & Admin Management (COMPLETE ✅)

**Plan artifact:** `step4_implementation_plan.md`

- Built robust Campaign state machine in `app/domain/campaign.py` and `app/services/campaign_service.py`:
  `DRAFT → PREPARING → OPEN → PAUSED → CLOSED → FROZEN → DRAWING → CLAIMING → COMPLETED`.
- Public endpoints implemented in `app/api/routes_campaigns.py`:
  - `GET /api/v1/campaigns`: lists active/public campaigns with pagination.
  - `GET /api/v1/campaigns/{id}`: detailed campaign metadata.
  - `GET /api/v1/campaigns/{id}/status`: lightweight polling endpoint for waiting room and client state sync.
- Admin endpoints implemented in `app/api/routes_admin.py`:
  - `POST /api/v1/admin/campaigns`: creates new campaign.
  - `PATCH /api/v1/admin/campaigns/{id}/status`: enforces legal state machine transitions.
  - `POST /api/v1/admin/campaigns/{id}/pause` & `POST /api/v1/admin/campaigns/{id}/resume`: emergency pause controls.
- Illegal transitions rejected with HTTP 409 and standard error envelope.

### Step 4.5 — Automated Integration Test Suite (COMPLETE ✅)

**Plan artifact:** `step4_5_implementation_plan.md`

- Built comprehensive Pytest test suite under `apps/backend/tests/`:
  - `conftest.py`: SQLite async in-memory database fixture with dynamic table creation, mock JWT generator, and FastAPI `AsyncClient`.
  - `test_health.py` (4 tests): verifies service readiness, DB ping, and envelope.
  - `test_auth.py` (8 tests): tests missing/invalid JWT, participant role, admin RBAC, 403 Forbidden, and JIT provisioning.
  - `test_campaigns.py` (6 tests): tests campaign retrieval, status polling, admin creation, valid lifecycle transitions, and illegal transition rejection (409).
- **Test Results**: 18 passed in 1.34s with 0 failures, 0 warnings.

### Step 4.6 — Supabase JWT Fetcher, Canary Flow & Asymmetric ES256 Support (COMPLETE ✅)

**Plan artifact:** `step4_6_implementation_plan.md` & `supabase_es256_jwks_auth_fix_plan.md`

- Built token fetcher script `apps/backend/scripts/get_supabase_token.py` using official Supabase Auth GoTrue API.
- Built end-to-end canary script `apps/backend/scripts/simulate_user_flow.py`.
- **Critical Auth Bug Solved**:
  - Modern Supabase projects issue asymmetric Elliptic Curve `ES256` tokens (`alg: "ES256"`) verified via JWKS, rather than symmetric `HS256`.
  - Added `cryptography>=43.0.0` to `pyproject.toml`.
  - Upgraded `app/security/jwt.py` to dual-mode decoder:
    1. Primary: Asymmetric `ES256` verified against Supabase JWKS endpoint (`https://gjbijluacysjudkvpivd.supabase.co/auth/v1/.well-known/jwks.json`) with cached keys.
    2. Fallback: Symmetric `HS256` using `SUPABASE_JWT_SECRET` for offline pytest mock tokens.
- Live test user confirmed: `tester@fairdrop.com` / `TestPassword123!` (Supabase UUID: `b14a1fae-74ae-4708-8427-9b87bf540e77`).
- Verified live `GET /auth/me` returning 200 with participant ID `b14a1fae-74ae-4708-8427-9b87bf540e77`.
- Git repository synced: branch `dd` pushed to `origin/dd`.

---

### Step 7 — Roster Freeze & Deterministic Uniform Lottery (COMPLETE ✅)

**Plan artifact:** `step7_implementation_plan.md`

- **Core Objective**: Execute a provably fair uniform lottery draw with committed randomness, immutable roster freezing, and deterministic winner/standby selection.
- **Implementation**:
  - Built `app/domain/lottery.py` & `app/services/lottery_service.py` with HMAC-SHA256 uniform pseudo-random number generator, Fisher-Yates shuffle variant over canonical participant list.
  - Implemented Roster Freeze (`POST /api/v1/admin/campaigns/{id}/freeze-roster`): selects accepted registrations, sorts deterministically, computes SHA-256 roster hash, transitions campaign to `FROZEN`.
  - Implemented Draw Execution (`POST /api/v1/admin/campaigns/{id}/draw`): consumes randomness seed/commitment, draws winners and standby queue, creates `lottery_runs` and `lottery_entries` rows, generates signed winner entitlements (`SELECTED`), transitions campaign to `CLAIMING`.
  - Public lottery result query: `GET /api/v1/campaigns/{id}/result`.
  - Pytest suite: `apps/backend/tests/test_lottery.py` (all tests passing).

---

### Step 8 — Atomic Seat Holds & Two-Phase Booking Redemption (COMPLETE ✅)

**Plan artifact:** `step8_implementation_plan.md`

- **Core Objective**: Implement high-concurrency atomic seat reservation, human-in-the-loop validation seam, and two-phase ticket redemption preventing overselling and race conditions.
- **Implementation**:
  - `app/domain/inventory.py` & `app/services/entitlement_service.py`: Row-level locking with `SELECT ... FOR UPDATE SKIP LOCKED` on `seats` table for zero oversell concurrency.
  - `POST /api/v1/entitlements/{id}/hold`: Holds an available seat for `SEAT_HOLD_SECONDS` (120s), transitions entitlement `SELECTED -> HELD`, persists hold row.
  - `POST /api/v1/entitlements/{id}/redeem`: Atomically confirms booking, transitions entitlement `HELD -> CONFIRMED`, updates seat status to `CONFIRMED`, consumes entitlement with single-use replay prevention.
  - `POST /api/v1/entitlements/{id}/release`: Voluntarily releases seat back to `AVAILABLE`.
  - Strict replay prevention: Duplicate or reused entitlement tokens rejected with `409 ENTITLEMENT_REPLAYED`.
  - Pytest suite: `apps/backend/tests/test_entitlements.py` (all tests passing).

---

### Steps 9 & 10 — Background Workers, Standby Promotion, Metrics & Verifiable Audit (COMPLETE ✅)

**Plan artifact:** `step9_10_implementation_plan.md`

- **Core Objective**: Reclaim expired holds, promote standby queue participants to winners, compute live fairness metrics, and expose immutable audit logs.
- **Implementation**:
  - Background Workers (`app/workers/`):
    - `hold_expiry_worker.py`: Reclaims expired seat holds and marks entitlements `EXPIRED`.
    - `entitlement_expiry_worker.py`: Invalidates unclaimed winner entitlements.
    - `standby_promotion_worker.py`: Promotes next available standby participant when seats become available.
    - `cleanup_worker.py`: Purges expired idempotency records.
    - `runner.py` & `scripts/run_workers_once.py`: Unified background task runner.
  - Standby Promotion Service (`app/services/standby_service.py`) and admin route `POST /api/v1/admin/campaigns/{id}/standby/process-next`.
  - Live Metrics Engine (`app/services/metrics_service.py`, `app/api/routes_metrics.py`): Real-time calculations of total attempts, unique participants, bot advantage ratio, oversell count, and winner distribution.
  - Public & Admin Verifiable Audit (`app/services/audit_query_service.py`, `app/api/routes_audit.py`): Immutable audit event logs with verification receipts.
  - Judge Demo Report Generator: `scripts/generate_fairness_report.py`.
  - Pytest suite: `apps/backend/tests/test_workers_and_metrics.py` (all tests passing).
  - **Overall Test Suite Status**: **37 / 37 PASSED**.

---

### Step 11 — Rate Limits, Hardening & Production Safety (COMPLETE ✅)

**Prompt file:** `prompt.md`
**Plan artifact:** `step11_implementation_plan.md`

- **Core Objective**: Harden the API against abuse, bot flooding, and oversized payloads while protecting legitimate users, preserving standard error envelopes, and guaranteeing zero disruption to health checks.
- **Implementation**:
  - `app/core/rate_limit_store.py`: In-memory sliding-window counter / token bucket rate limiter with abstract `BaseRateLimitStore` interface for future Redis scaling.
  - `app/middleware/rate_limit.py`: Global IP rate limiter (`RL_GLOBAL_IP_PER_MIN=300`) and scoped route-level limiter returning `429 RATE_LIMITED` with standard envelope and `Retry-After` header. Exempts `/health`, `/`, and docs.
  - `app/middleware/security_headers.py`: Standard security headers (`nosniff`, `DENY`, `no-referrer`, `no-store` on sensitive auth/registration/entitlement endpoints) and 64KB request body size guard (`413 PAYLOAD_TOO_LARGE`).
  - Input hardening: Strict `Idempotency-Key` validation on mutation routes (`400 IDEMPOTENCY_KEY_REQUIRED`).
  - Production error masking: Generic 500 error envelopes without internal stack trace leakage in non-development modes.
  - Idempotency interaction: Replays with matching key & hash return cached responses without tripping rate limits.
  - Operational scripts: `scripts/test_rate_limits.py`, `scripts/security_smoke_test.py`, and `scripts/simulate_user_flow.py` with judge summary table.
  - Pytest suite: `apps/backend/tests/test_hardening_and_rate_limits.py` (**6/6 PASSED**).
  - **Overall Test Suite Status**: **43 / 43 PASSED**.

---

## 6. Testing Performance Diagnosis (Why Testing Took Long)

1. **Remote Cloud Supabase PostgreSQL Latency**:
   - `DATABASE_URL` connects over WAN to Supabase pooler in AWS Asia-South-1 (`aws-0-ap-south-1.pooler.supabase.com:6543/postgres`).
   - Every live script roundtrip incurs SSL handshake and WAN network latency.
   - When scripts generate dozens to hundreds of rows (e.g. 500 seats, permits, entries) sequentially over WAN, execution time multiplies significantly.
2. **Directory Context for Pytest**:
   - `pyproject.toml` containing `asyncio_mode = "auto"` is inside `apps/backend/`. Running `pytest` from repository root instead of `apps/backend` causes async discovery issues.
3. **Optimizing Test Execution**:
   - Unit and integration tests in `apps/backend/tests/` use fast in-memory SQLite fixtures (`conftest.py`), running the entire 37+ test suite in ~2 seconds.
   - Live network tests should be reserved for canary scripts (`simulate_user_flow.py`) or run with minimal batch sizes.

---

## 7. Immediate next actions

### Dhruv — Step 11 Execution
1. Implement `app/config.py` with `RL_*` rate limit knobs and payload size limits.
2. Implement `app/core/rate_limit_store.py` (in-memory sliding window rate limiter).
3. Implement `app/middleware/security_headers.py` and `app/middleware/rate_limit.py`.
4. Register middleware in `app/main.py`.
5. Implement `scripts/test_rate_limits.py` and `scripts/security_smoke_test.py`.
6. Implement `tests/test_hardening_and_rate_limits.py` and run full pytest suite.
7. Run `scripts/simulate_user_flow.py --in-process` to verify end-to-end integration and judge summary.
