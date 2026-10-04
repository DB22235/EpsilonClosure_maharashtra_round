# FairDrop Backend — Master Integration & Handoff Guide

Welcome to the **FairDrop Backend** codebase! This document is designed for engineers integrating, navigating, running, and testing the FairDrop high-concurrency ticket allocation and anti-bot verification backend.

---

## 1. System Overview & Tech Stack

FairDrop is an enterprise-grade seat allocation system engineered for fairness, cryptographic auditability, and resistance against automated scalping bots.

- **Framework**: FastAPI (async ASGI) with Python 3.11 / 3.12 / 3.13.
- **Database & ORM**: PostgreSQL via `asyncpg` and SQLAlchemy 2.0 (Strict Async, Row-Level Locking with `FOR UPDATE SKIP LOCKED`).
- **Auth Provider**: Supabase Auth (GoTrue) using HS256 / RS256 JWTs with local PostgreSQL profile synchronization and role-based access control (`ADMIN` vs `USER`).
- **Verification Engine**: Embedded MediaPipe 21-landmark geometric challenge engine (`mediapipe_engine/`) with single-use nonce validation and rate-limited cooldowns.
- **Background Tasks**: Server-authoritative expiry workers for 120s seat holds, redemption deadlines, and standby promotions.

---

## 2. Virtual Environment FAQ: Which `.venv` Should I Use?

### The Question: *"Why were there two `.venv` folders and which one do I use?"*
1. **The Root `.venv`**: Was originally created during early monorepo experiments.
2. **`backend/.venv`**: This is the **authoritative backend virtual environment** where the FastAPI server, tests, and database migrations run.

> [!IMPORTANT]
> **CRITICAL RULE FOR HANDOFF**:
> Python virtual environments **CANNOT be copied between computers or operating systems**. Virtualenv scripts contain hardcoded absolute filesystem paths pointing to the author's machine.
> 
> When you pull or extract this folder, **create your own fresh `.venv`** inside `backend/` using the instructions below.

### Fresh Environment Setup (Takes 60 seconds)

#### On Windows (PowerShell):
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
```

#### On Linux / macOS (Bash / Zsh):
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
```

*Note: Running `pip install -e .` installs `app`, `scripts`, and `mediapipe_engine` in editable mode, allowing imports like `from app.config import lru_settings` and `from mediapipe_engine.gesture_engine import GestureEngine` everywhere without path headaches.*

---

## 3. Clean Backend Architecture & Directory Map

```
backend/
├── app/                        # Main application package
│   ├── api/                    # HTTP Router & API Endpoints
│   │   ├── router.py           # Master router aggregator (mounts /api/v1)
│   │   ├── routes_admin.py     # Campaign creation, freeze, and lottery draw
│   │   ├── routes_audit.py     # Verifiable cryptographic audit trail & fairness verification
│   │   ├── routes_auth.py      # Login, registration, token exchange, and confirmation
│   │   ├── routes_campaigns.py # Public campaign catalog, details, waiting room, results
│   │   ├── routes_challenges.py# MediaPipe ML challenge issuance, verification, telemetry
│   │   ├── routes_entitlements.py# 120s seat holds (SKIP LOCKED), hold release, and claim
│   │   ├── routes_health.py    # Liveness & readiness probes (/health)
│   │   ├── routes_metrics.py   # Latency, failure rates, challenge analytics
│   │   └── routes_registration.py# Campaign lottery registration and risk gate checks
│   ├── core/                   # Core stores (In-memory rate limit store)
│   ├── domain/                 # State machines & business domain rules (Campaign FSM)
│   ├── integrations/           # External adapters (ChallengeAdapter, Turnstile)
│   ├── middleware/             # HTTP middleware (Rate limiting, Security headers)
│   ├── models/                 # SQLAlchemy 2.0 DB models (Base, Campaign, Seat, etc.)
│   ├── repositories/           # DB data-access repositories
│   ├── schemas/                # Pydantic v2 validation contracts (Request/Response)
│   ├── security/               # Cryptographic hashing, single-use nonces, JWT verification
│   ├── services/               # Core business services (Lottery, Entitlements, Admission)
│   ├── workers/                # Background async workers (Hold expiry, cleanup, standby)
│   ├── config.py               # Pydantic Settings & environment variable configuration
│   ├── database.py             # Async engine, connection pool, and session factory
│   ├── dependencies.py         # FastAPI dependency injection (DB sessions, Auth context)
│   └── main.py                 # FastAPI application factory and lifespan manager
│
├── mediapipe_engine/           # Embedded ML gesture challenge engine
│   ├── detectors/              # Geometric detectors (Thumbs Up, Swipe, Move)
│   ├── cv_utils.py             # Landmark math, vector calculations, bounding boxes
│   ├── gesture_engine.py       # Replay verification & single-use nonce validation
│   └── verifier.py             # Client submission verifier
│
├── migrations/                 # Alembic database schema migrations
│   ├── versions/               # Versioned migration scripts
│   └── env.py                  # Alembic async migration runner
│
├── scripts/                    # Developer & Operational CLI Tools
│   ├── seed_demo_accounts.py   # One-command demo accounts provisioner (Admin & User)
│   ├── create_user.py          # Custom user creation utility (--email, --password, --role)
│   ├── seed_demo_campaign.py   # Generates sample open campaigns with seat maps
│   ├── simulate_user_flow.py   # Full CLI simulation (Register -> Draw -> Hold -> Claim)
│   ├── test_rate_limits.py     # Penetration test script for 429 rate limit enforcement
│   ├── generate_fairness_report.py# Cryptographic proof & fairness distribution visualizer
│   ├── promote_admin.py        # Promotes any existing user UUID to ADMIN role
│   ├── reset_database.py       # Safe development database clean & reset utility
│   └── run_workers_once.py     # Runs background expiry jobs once on demand
│
├── tests/                      # Automated Pytest Test Suite
│   ├── conftest.py             # Fixtures, test DB, mock JWT auth headers
│   ├── test_auth.py            # Authentication & RBAC tests
│   ├── test_campaigns.py       # Campaign creation, publishing, and lifecycle
│   ├── test_registration.py    # Anti-sybil lottery registration & validation
│   ├── test_lottery.py         # Deterministic cryptographic lottery draw tests
│   ├── test_entitlements.py    # 120s seat hold concurrency & redemption tests
│   ├── test_booking_end_to_end_flow.py # Complete end-to-end lifecycle integration
│   ├── test_hardening_and_rate_limits.py # Abuse prevention & burst protection
│   └── test_workers_and_metrics.py # Background worker expiry & metrics tests
│
├── .env.example                # Sanitized environment configuration template
├── .gitignore                  # Airtight protection against secrets, caches, and dumps
├── alembic.ini                 # Alembic configuration
├── pyproject.toml              # Build metadata & dependency definitions
├── requirements.txt            # Pinned runtime dependencies
├── requirements-dev.txt        # Development dependencies (pytest, ruff)
└── openapi.json                # Exported OpenAPI 3.1 specification for frontend codegen
```

---

## 4. Environment Configuration (`.env`)

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Inspect the configuration keys:

| Environment Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `APP_ENV` | Application environment | `development` |
| `API_V1_PREFIX` | Base route prefix | `/api/v1` |
| `DATABASE_URL` | PostgreSQL Async connection string | `postgresql+asyncpg://user:password@localhost:5432/fairdrop` |
| `SUPABASE_URL` | Supabase project URL | `https://gjbijluacysjudkvpivd.supabase.co` |
| `SUPABASE_ANON_KEY`| Supabase public anon key | *(See `.env.example`)* |
| `SUPABASE_JWT_SECRET`| Secret used to verify HS256 user JWTs | *(See `.env.example`)* |
| `EMAIL_HASH_PEPPER`| Salt used for privacy-preserving email hashing | `fair-drop-dev-pepper-change-me` |
| `SEAT_HOLD_SECONDS`| Duration a winning participant holds a seat | `120` (2 minutes) |
| `COOLDOWN_SECONDS` | Cooldown penalty after 3 failed challenges | `300` (5 minutes) |
| `MAX_CHALLENGE_ATTEMPTS` | Attempts per challenge nonce | `2` |
| `CORS_ORIGINS` | Allowed frontend origins | `["http://localhost:3000"]` |

---

## 5. Seed Pre-Configured Demo Accounts

To avoid manual user sign-up and auto-confirm steps, run the dedicated demo account seeder:

```bash
python -m scripts.seed_demo_accounts
```

This provisions and confirms the following accounts in both Supabase GoTrue Auth and PostgreSQL:

| Role | Email | Password | Intended Portal |
| :--- | :--- | :--- | :--- |
| **ADMIN** | `admin@fairdrop.com` | `AdminPassword123!` | `/admin/login` |
| **USER** | `user@fairdrop.com` | `UserPassword123!` | `/login` |
| **ADMIN (Secondary)**| `ntc3108@gmail.com` | `Password123!` | `/admin/login` |

---

## 6. How to Run the Application

Start the FastAPI application with auto-reload:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Once running:
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 7. Complete User Lifecycle & Route Sequence

When integrating with the frontend or calling the API via Postman/cURL, follow this exact state progression:

```mermaid
sequenceDiagram
    autonumber
    actor User as Participant
    actor Admin as Admin Operator
    participant API as FairDrop API (/api/v1)
    participant DB as PostgreSQL
    participant ML as MediaPipe Engine

    Note over User,API: 1. Authentication
    User->>API: POST /auth/login (email, password)
    API-->>User: Bearer JWT Token

    Note over User,API: 2. Anti-Bot ML Challenge (If Risk Gate Triggers)
    User->>API: POST /challenges (campaign_id, type="MEDIAPIPE")
    API-->>User: Challenge Issued (nonce, gesture instructions, camera bounds)
    User->>ML: Performs gesture in camera HUD
    User->>API: POST /challenges/{id}/verify (nonce, landmarks, hand_used)
    API-->>User: status: "PASSED", reason_code: "CHALLENGE_PASSED"

    Note over User,API: 3. Campaign Lottery Registration
    User->>API: POST /campaigns/{id}/register
    API-->>User: Registered (status: "REGISTERED", position queued)

    Note over Admin,API: 4. Admin Freeze & Lottery Execution
    Admin->>API: POST /admin/campaigns/{id}/freeze
    API-->>Admin: Roster frozen
    Admin->>API: POST /admin/campaigns/{id}/draw (randomness_seed)
    API-->>Admin: Uniform Lottery Completed (Entitlements Issued)

    Note over User,API: 5. Lottery Results & Seat Hold
    User->>API: GET /campaigns/{id}/result
    API-->>User: status: "WON", entitlement_id: "<UUID>"
    User->>API: POST /campaigns/{id}/holds (Idempotency-Key: "<uuid>")
    Note over API,DB: Locks seat with FOR UPDATE SKIP LOCKED
    API-->>User: Seat Held (seat_label: "A-1", hold_expires_at: "+120s")

    Note over User,API: 6. Final Ticket Claim
    User->>API: POST /campaigns/{id}/claim (entitlement_id, seat_id)
    API-->>User: status: "CONFIRMED" (QR Code / Ticket payload issued)
```

---

## 8. Testing & Validation

### Run Pytest Integration Suite
```bash
pytest -v
```

### Run Standalone ML Challenge Tests (No DB needed)
```bash
python handoff_bundle/test_scripts/test_mediapipe_standalone.py
```
*Expected: 15 passed in ~0.5s verifying `THUMBS_UP`, `SWIPE`, `MOVE`, and `HAND_MISMATCH` geometry.*

### Run End-to-End User Simulation CLI
```bash
python -m scripts.simulate_user_flow
```

### Run Rate-Limit Penetration Smoke Test
```bash
python -m scripts.test_rate_limits
```

---

## 9. Connecting to the Next.js Frontend

The Next.js frontend is located in `/frontend`.
To connect the frontend to your local running backend:

1. In `/frontend`, copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```
2. Verify that `NEXT_PUBLIC_API_BASE_URL` points to `http://localhost:8000/api/v1`.
3. Set `NEXT_PUBLIC_DEMO_MODE=false` to test against the live backend.
4. Launch the frontend:
   ```bash
   cd frontend
   npm run dev
   # or
   pnpm dev
   ```
5. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 10. Key Architectural Decisions & Gotchas

1. **Strict Idempotency**:
   - Every state-mutating POST (such as `/holds` and `/claim`) accepts an `Idempotency-Key` header.
   - If a network drop occurs, retrying with the same key returns the exact original result without creating a duplicate hold or claiming two tickets.
2. **Server-Authoritative Clock**:
   - Seat holds expire strictly 120 seconds after creation. Clients must rely on `hold_expires_at` from the server response rather than local device clocks.
3. **Challenge Foreign Keys**:
   - Every challenge must be associated with an active session in the `sessions` table. [`routes_challenges.py`](file:///c:/Users/Dhruv%20Dube/Desktop/hackathons/ty/BNB/EpsilonClosure_maharashtra_round/backend/app/api/routes_challenges.py) handles this automatically via `_get_or_create_session`.
4. **Cooldown Protection**:
   - 3 consecutive failed or expired challenges within 300 seconds will activate a temporary lockout returning `HTTP 429 Too Many Requests` with `code: "COOLDOWN_ACTIVE"`.
