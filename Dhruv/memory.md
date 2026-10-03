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

**Plan artifact:** `step1_implementation_plan.md` (full per-file specification followed)

**Scope confirmed and executed:**
All 17 files created strictly within `/apps/backend/`. Zero files outside. Zero business logic, zero database, zero auth.

Files created (17 total, in dependency-safe order):

```text
/apps/backend/
  .gitignore               — Python standard + .venv + .env + ruff/pytest caches
  .env.example             — all 15 env vars; SUPABASE_URL pre-filled with real URL
  pyproject.toml           — exact pinned deps; ruff config; pytest asyncio_mode=auto
  README.md                — setup, endpoints, and run instructions
  app/__init__.py          — package marker
  app/config.py            — pydantic-settings Settings class + lru_settings()
  app/api/__init__.py      — package marker
  app/api/router.py        — APIRouter stub (v1_router) with prefix; zero routes
  app/domain/__init__.py   — package stub
  app/models/__init__.py   — package stub
  app/schemas/__init__.py  — package stub
  app/repositories/__init__.py  — package stub
  app/services/__init__.py      — package stub
  app/security/__init__.py      — package stub
  app/integrations/__init__.py  — package stub
  app/workers/__init__.py       — package stub
  app/main.py              — FastAPI app; asynccontextmanager lifespan; CORS; GET /; GET /health
```

**Key decisions implemented:**

- `pyproject.toml`: `fair-drop-backend`, Python `>=3.11.9,<3.12`. Six runtime deps (`fastapi==0.115.6`, `uvicorn[standard]==0.34.0`, `pydantic==2.10.4`, `pydantic-settings==2.7.1`, `python-dotenv==1.0.1`, `httpx==0.28.1`) + three dev deps pinned. `[tool.ruff]` with `line-length=100`, `target-version="py311"`. Added `[tool.pytest.ini_options] asyncio_mode = "auto"`.
- `.env.example`: All 15 variables. `SUPABASE_URL` pre-filled with `https://gjbijluacysjudkvpivd.supabase.co`. `CORS_ORIGINS` as JSON array string. `REDIS_URL` blank (not null). `APP_ENV=development`.
- `config.py`: `BaseSettings`, `SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)`. `APP_ENV` as `Literal["development","demo","production"]`. `CORS_ORIGINS` as `list[str]` with `@field_validator` handling JSON list, string list, and fallback. `lru_cache(maxsize=1)` on `lru_settings()`. Default values for all fields matching `.env.example`.
- `main.py`: `@asynccontextmanager` lifespan (NOT deprecated `on_event`). `datetime.now(timezone.utc)` for health timestamp (NOT deprecated `utcnow()`). CORS from `settings.CORS_ORIGINS`. Root `GET /` and `GET /health` endpoints. `v1_router` NOT mounted.
- `router.py`: `v1_router = APIRouter(prefix=lru_settings().API_V1_PREFIX)`. Named `v1_router` explicitly. Placeholder comment. Zero routes.

**Verification results:**
- 17 files exist under `/apps/backend/`.
- Virtual environment created and dependencies installed (`fastapi==0.115.6`, `uvicorn==0.34.0`, `pydantic==2.10.4`, `pydantic-settings==2.7.1`, `httpx==0.28.1`, `pytest==8.3.4`, `ruff==0.8.6`).
- `ruff check .` → All checks passed (0 errors).
- `config.py` loads correctly: `APP_ENV=development`, `CORS_ORIGINS=['http://localhost:3000']`, `SUPABASE_URL=https://gjbijluacysjudkvpivd.supabase.co`.
- `GET /` → `200 {"service": "fair-drop", "status": "running", "version": "0.1.0"}` verified via test client.
- `GET /health` → `200 {"status": "healthy", "timestamp": "2026-10-03T...Z"}` verified via test client.
- OpenAPI schema has exactly 2 routes: `['/', '/health']`.
- Zero database imports or models in `app/`.
- Zero auth imports or client code in `app/`.

### Step 2 — Database & Foundation Models (Next up)

- Add asyncpg + SQLAlchemy async + Alembic to `pyproject.toml`.
- Create database connection module (`app/db/session.py`) and session dependency (`app/dependencies.py`).
- Initialize Alembic migration environment under `/apps/backend/migrations/`.
- Create initial migrations for all core tables (`campaigns`, `profiles`, `participants`, `sessions`).
- Wire readiness check into `/health` (DB ping).

## 6. Immediate next actions

### Dhruv — Step 2 (Database & Persistence)

- Configure async SQLAlchemy 2.0 with asyncpg driver.
- Set up sessionmaker and `get_db` FastAPI dependency with auto-commit/rollback handling.
- Initialize Alembic migrations.
- Create ORM models for `campaigns`, `profiles`, `participants`, and `sessions`.
- Update `/health` endpoint with database ping check.

### Dhruv — Step 2 (after Step 1 passes verification)

- Add asyncpg + SQLAlchemy async + Alembic to pyproject.toml.
- Create database connection module and session dependency.
- Initialize Alembic migration environment.
- Create initial migrations for all core tables.
- Wire readiness check into `/health` (DB ping).

### Rohan

- Initialize `/apps/frontend` from the existing team template.
- Build event, waiting room, registration, result, redemption, and dashboard states against mock API.
- Implement server-state recovery on refresh/reconnect.
- Integrate challenge and metrics contracts after they are published.

### Dhanya

- Initialize `/apps/simulator`.
- Implement scenario configuration and normal-human profile.
- Add fast, burst, retry, account-farm, direct-API, replay, race, shared-network, and slow-user profiles.
- Define JSON/CSV report format.
- Build first mixed-traffic test against Dhruv's API/mock server.

### Naman

- Verify Python 3.11.9 and initialize `/apps/mediapipe/.venv`.
- Implement first gesture challenge with deterministic mock mode.
- Define challenge result contract, nonce, expiry, and fallback behavior.
- Add remaining challenges after the first one is integrated.

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
