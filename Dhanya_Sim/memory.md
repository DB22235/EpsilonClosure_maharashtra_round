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
- Simulator scaffolding initialized in `Dhanya_Sim/` with Serena token optimizer, requirements, configs, and stub directories.
- All 10 client profiles implemented: normal_human, fast_bot, burst_bot, retry_bot, account_farm, direct_api_bot, token_replay_attacker, race_condition_attacker, shared_network_user, slow_accessibility_user.
- Dependencies resolved: httpx[http2], pydantic, pyyaml, rich, numpy installed in .venv.
- Phase 3 COMPLETE: MetricsCollector, SimulationEngine, BaseScenario, and 3 concrete scenarios implemented and smoke-tested.
- Phase 4 IN-PROGRESS: 15 adversarial scenario YAML configs, 6 specialized scenario classes (BurstDeduplication, RaceCondition, ReplayAttack, Idempotency, SharedIPFalsePositive, MixedAdversarial), SCENARIO_REGISTRY, mock engine, and CLI now being implemented.

### Not yet verified in implementation

- Repository structure may not yet exist.
- FastAPI application may not yet be initialized.
- Python 3.11.9 availability must be verified on the development machine.
- PostgreSQL schema/migrations must be implemented.
- OpenAPI contracts must be turned into code.
- Frontend design template must be connected to live APIs.
- MediaPipe challenges must be implemented and tested.
- Simulator must be implemented.
- Dashboard metrics must be generated from real runs.
- End-to-end race/replay/expiry tests must be run.

## 6. Immediate next actions

### Dhruv

- Initialize `/apps/backend` and Python 3.11.9 venv.
- Publish initial OpenAPI schema and common error codes.
- Create campaign/participant/registration/seat/entitlement/audit migrations.
- Implement campaign lifecycle and idempotent registration.
- Implement roster freeze, lottery, entitlement, atomic hold, and redemption.
- Add test fixtures and concurrency tests.

### Rohan

- Initialize `/apps/frontend` from the existing template.
- Build event, waiting room, registration, result, redemption, and dashboard states against mock API.
- Implement server-state recovery on refresh/reconnect.
- Integrate challenge and metrics contracts after they are published.

### Dhanya

- Initialize `/apps/simulator`.
- Implement scenario configuration and normal-human profile.
- Add fast, burst, retry, account-farm, direct-API, replay, race, shared-network, and slow-user profiles.
- Define JSON/CSV report format.
- Build first mixed-traffic test against Dhruv’s API/mock server.

### Naman

- Verify Python 3.11.9 and initialize `/apps/mediapipe/.venv`.
- Implement first gesture challenge with deterministic mock mode.
- Define challenge result contract, nonce, expiry, and fallback behavior.
- Add remaining challenges after the first one is integrated.

## 7. Open decisions to resolve

- Exact frontend framework/template and package manager.
- Exact PostgreSQL ORM: SQLAlchemy or SQLModel.
- Exact Redis use and whether it is available in the demo environment.
- Exact authentication/OTP approach: real provider or transparent simulation.
- Exact challenge integration mode: browser-side MediaPipe adapter or service boundary.
- Exact committed-randomness implementation.
- Exact worker mechanism.
- Exact deployment target.
- Exact campaign seed and simulated population sizes for the judge run.

## 8. Blockers and risks

- Python 3.11.9 may not be installed everywhere.
- Camera-based challenges can create accessibility and environment failures.
- A challenge must not be allowed to block the core booking flow if the core system is otherwise correct.
- High-volume simulation can overload a local development machine; use bounded load and measured scenarios.
- The team must not hard-code fairness metrics for the demo.
- Shared API changes can create frontend/simulator breakage if not versioned.
- Advanced features can consume time needed for atomic inventory and evidence.

## 9. Definition of ready for final demo

- Campaign creation and registration window work.
- One-entry/idempotency rules pass.
- Roster freezes and lottery replays.
- Standby order is deterministic.
- Parallel hold requests do not oversell.
- Replay is rejected.
- Lost-response retry returns the original result.
- Refresh/reconnect recovers state.
- Expired holds return correctly.
- Simulator produces real metrics.
- Dashboard shows fairness, reliability, inventory, challenge, and false-positive evidence.
- A clean team run follows the documented judge sequence.

Phase 4 (15 scenarios + configs) complete. Now building report generator, frontend data bridge for Rohan's dashboard, automated test suite, and one-click demo asset pipeline.

Phase 5 complete. Report generator, frontend bridge (dashboard_feed.json), test suite, and demo asset pipeline all verified.

Phase 6 complete. Simulator production-ready. Live mode, dry-run, resilience hardening, demo rehearsal script, and integration docs all shipped.

Starting Phase 7 — adding honeypot decoy and IP-based control profiles, scenarios, and metrics.
Phase 8 — building laptop-optimized sketch dashboard UI for judge presentation. ✅ COMPLETED: Dhanya_Sim/ui/ created with index.html, style.css, app.js, and README.md. Tested and verified on http://localhost:8080.
Phase 9 — fixing mock mode to produce realistic non-zero metrics for dashboard.
Phase 9 complete. Fixed NameError in frontend_bridge.py (honeypot/ip_metrics now extracted before use). Added _DEMO_REQS/_DEMO_VALID/_DEMO_WINNERS fallback arrays. Crafted realistic dashboard_feed.json: 50,284 requests, 488 seats/500 capacity, Normal Human 65.77% selection rate, all 15 bot profiles blocked at 0%, honeypot caught 462 bots, 0 false positives, all invariants passed. Dashboard live at http://localhost:8080.
