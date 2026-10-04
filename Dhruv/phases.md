# Fair Drop — Required Implementation Phases

The project is divided into **8 required phases**. Each phase has an exit condition. The team should not move to polish while a previous phase is failing its correctness criteria.

## Phase 1 — Contract and repository foundation (COMPLETE ✅)

### Goal
Create the shared working structure so four people can work independently without merge conflicts.

### Work

- Create `/apps/backend`, `/apps/frontend`, `/apps/simulator`, `/apps/mediapipe`.
- Create `/packages/api-contract` and `/docs`.
- Publish initial API/OpenAPI schemas.
- Confirm branch and commit conventions.
- Confirm Python 3.11.9 for Naman and Dhruv.
- Add environment-variable templates, not secrets.
- Add basic CI/test commands.

### Exit criteria

All four workspaces start independently, owners are clear, and frontend/simulator can use mock API responses.

## Phase 2 — Default live-website foundation (COMPLETE ✅)

### Goal
Build the minimum secure, observable web platform.

### Work

- FastAPI startup and health/readiness endpoints (Step 1).
- PostgreSQL connection with asyncpg + SQLAlchemy 2.0 (Step 2).
- All 17 core tables initialized in Supabase PostgreSQL (Step 2).
- Authentication and session skeleton with Supabase JWT + JIT provisioning (Step 3).
- Campaign state machine and admin controls (Step 4).
- Request IDs, structured errors, logging, validation.
- 18/18 integration tests passed (Step 4.5).
- Dual-mode ES256 JWKS + HS256 auth verification (Step 4.6).

### Exit criteria

The application starts from a clean environment, performs authenticated API calls, persists a test record, and reports health correctly. **PASSED.**

## Phase 3 — Campaign and fair registration (IN PROGRESS ⏳ — Step 5)

### Goal
Implement one valid registration per participant.

### Work

- Campaign creation and state machine (COMPLETE).
- Registration window using server time (COMPLETE).
- Participant/verification model (COMPLETE).
- Admission permit generation and HMAC-SHA256 signature (Step 5).
- Registration endpoint with `Idempotency-Key` header (Step 5).
- Idempotency records and request hashes (Step 5).
- Unique campaign/participant constraint enforcement (Step 5).
- Refresh/reconnect status endpoint recovery slice (Step 5).
- Challenge seam integration with Naman (Step 5).

### Exit criteria

Normal registration works; duplicate submissions and retry-after-timeout do not create extra entries; registration closes correctly.

## Phase 4 — Roster freeze and auditable allocation (PENDING)

### Goal
Make allocation fair, reproducible, and inspectable.

### Work

- Freeze eligible roster.
- Canonical ordering and roster hash.
- Committed randomness reference.
- Uniform lottery.
- Winner and fixed standby order.
- Lottery audit record.
- Result and private fairness receipt endpoints.

### Exit criteria

The same frozen roster and randomness reproduce the same result. No registration changes after freeze. Winner and standby results are visible.

## Phase 5 — Atomic claims and inventory integrity

### Goal
Guarantee no overselling or duplicate ownership under concurrency.

### Work

- Seat model and `AVAILABLE → HELD → CONFIRMED` states.
- Single-use winner entitlements.
- Server-side idle, absolute, and hold timers.
- Atomic hold transaction.
- Atomic redemption transaction.
- Expiry worker.
- Standby promotion.
- Replay protection.

### Exit criteria

Parallel requests cannot oversell; one seat cannot have two owners; expired holds return safely; replayed entitlements fail.

## Phase 6 — Abuse handling and human validation

### Goal
Add risk-based friction without claiming perfect bot detection.

### Work

- Endpoint-specific rate limits.
- Risk score and reason codes.
- Cooldown state.
- Challenge adapter.
- Turnstile integration if ready.
- MediaPipe integration through Naman’s contract.
- Visual/accessibility fallback.
- Admission and entitlement replay checks.

### Exit criteria

Suspicious behavior triggers documented friction/cooldown; legitimate shared-network and slow users are not automatically rejected; challenge results are server-bound and one-time.

## Phase 7 — Adversarial simulation and evidence

### Goal
Prove behavior with real traffic classes and measurements.

### Work

- Normal human profile.
- Fast/burst/retry bots.
- Account farm.
- Direct API bot.
- Token replay attacker.
- Race-condition attacker.
- Shared-network user.
- Slow/accessibility user.
- Latency, error, fairness, inventory, false-positive metrics.
- JSON/CSV reports and dashboard integration.

### Exit criteria

The simulator can reproduce attacks; results show raw requests versus valid entries; integrity invariants pass; metrics are not hard-coded.

## Phase 8 — Integration, demo hardening, and release

### Goal
Create a reliable, judge-ready demonstration.

### Work

- Run complete end-to-end flow.
- Test refresh/reconnect and lost-response retry.
- Test worker restart and database/cache failure behavior where possible.
- Confirm API contract compatibility.
- Confirm no owned-directory collisions.
- Add public audit page and operator dashboard.
- Prepare demo script and fallback screenshots/data.
- Run final security and dependency review.
- Package deployment instructions.

### Exit criteria

The 21-step judge demonstration runs successfully from campaign creation through audit evidence, with zero oversell and zero duplicate allocation in the recorded run.

## Phase ordering rule

Do not build advanced challenge games, payment integration, Merkle proofs, or multi-region deployment before Phases 3–5 are stable. The core proof is registration integrity, auditable allocation, and atomic inventory.
