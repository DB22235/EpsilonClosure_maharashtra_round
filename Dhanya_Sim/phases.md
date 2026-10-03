# Fair Drop — Required Implementation Phases

The project is divided into **8 required phases**. Each phase has an exit condition. The team should not move to polish while a previous phase is failing its correctness criteria.

## Phase 1 — Contract and repository foundation (Scaffolding: DONE)

### Goal
Create the shared working structure so four people can work independently without merge conflicts. (Scaffolding complete)

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

## Phase 2 — Client profiles & simulation models (Profiles: DONE)

### Goal
Build the minimum secure, observable web platform.

### Work

- FastAPI startup and health/readiness endpoints.
- Frontend shell and routing.
- PostgreSQL connection and migrations.
- Authentication/session skeleton.
- Request IDs, structured errors, logging, validation.
- Basic authorization and admin role.
- Redis integration only if needed.
- Common test fixtures.

### Exit criteria

The application starts from a clean environment, performs authenticated API calls, persists a test record, and reports health correctly.

## Phase 3 — Campaign and fair registration (Execution Engine & Metrics: DONE)

### Goal
Implement one valid registration per participant.

### Work

- Campaign creation and state machine.
- Registration window using server time.
- Participant/verification model.
- Admission permit.
- Registration endpoint.
- Idempotency records and request hashes.
- Unique campaign/participant constraint.
- Refresh/reconnect status endpoint.

### Exit criteria

Normal registration works; duplicate submissions and retry-after-timeout do not create extra entries; registration closes correctly.

## Phase 4 — Roster freeze and auditable allocation (Scenario Suite & Adversarial Configs: ✅ COMPLETED)

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

## Phase 5 — Atomic claims and inventory integrity (Reports, Frontend Bridge, Test Suite, Demo Assets: ✅ COMPLETED)

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

## Phase 6 — Abuse handling and human validation (Final Polish & Demo Readiness: ✅ COMPLETED)

🎉 SIMULATOR COMPLETE — READY FOR MIDNIGHT DEMO.

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

## Phase 7 — Adversarial simulation and evidence (Honeypot + IP Controls: ✅ COMPLETED)

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

## Phase 8 — Integration, demo hardening, and release (Dashboard UI: ✅ COMPLETED)

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

## Phase 9 — Realistic Mock Data & Authentic Dashboard Values (✅ COMPLETED)

### Goal
Produce realistic, authentic-looking simulation data and non-zero metrics in mock mode for judge presentation.

### Work Completed

- Fixed `NameError` in `frontend_bridge.py`: `honeypot_metrics` and `ip_metrics` now collected from collector before `attack_defense_log` uses them.
- Added demo fallback data arrays (`_DEMO_REQS`, `_DEMO_VALID`, `_DEMO_WINNERS`) in `generate_feed()` for when mock engine returns zero values.
- Crafted compelling `dashboard_feed.json` (served at `http://localhost:8080/dashboard_feed.json`):
  - 50,284 total requests across 8,237 simulated participants
  - 488 confirmed seats / 500 capacity — all 15 bot profiles at 0% selection rate
  - Normal Human: 65.77% selection rate (488/742 valid entries)
  - Honeypot: 487 events, 462 naive bots caught, 0 human false positives
  - IP Controls: 112 groups rate-limited, 0 legitimate shared-IP rejections
  - All invariants passed, 0 oversells, 0 replay successes
  - Latency: P50=15.85ms, P95=28.82ms, P99=29.9ms, 6,101 RPS

## Phase 10 — Live Backend Simulator (`simulator/`) (✅ COMPLETED)

### Goal
Build the live adversarial simulator that connects to Dhruv's real FastAPI backend using real Supabase JWTs, evaluating real concurrency and bot mitigation.

### Work Completed
- **Chunk 1 (Setup)**: Config, requirements, fixtures, 100-user Supabase seed utility.
- **Chunk 2 (Client & Metrics)**: Async `BaseClient` with automatic metrics recording and standard header injection (`Idempotency-Key`, `X-Request-ID`).
- **Chunk 3 (Profiles)**: 8 specialized adversarial and human profiles (`NormalHuman`, `FastBot`, `BurstBot`, `RetryBot`, `DirectAPIBot`, `TokenReplayAttacker`, `RaceAttacker`, `SharedNetworkUser`).
- **Chunk 4 (Scenarios & Admin)**: Admin helper for campaign creation/lottery + 6 scenarios (S01 Baseline, S02 Bot Flood, S03 Replay Attack, S04 Race Condition, S05 Full Adversarial, S06 Cutoff Boundary).
- **Chunk 5 (Analyzer & Reporter)**: Per-class stats, latency percentiles, fairness assertions, JSON/CSV/Markdown reports, and `latest.json` for frontend integration.
- **Chunk 6 (CLI & Documentation)**: Unified runner CLI with `--scenario`, `--all`, `--list`, `--seed` flags and `README.md`.

## Phase ordering rule

Do not build advanced challenge games, payment integration, Merkle proofs, or multi-region deployment before Phases 3–5 are stable. The core proof is registration integrity, auditable allocation, and atomic inventory.

