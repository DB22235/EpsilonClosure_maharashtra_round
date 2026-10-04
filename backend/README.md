# Fair Drop — Backend

Fair Drop is a high-demand event seat allocation platform designed to ensure fair, transparent, and bot-resistant ticket distribution. The platform integrates cryptographically signed permits, fair queue mechanics, embedded MediaPipe ML challenge verification, and strict server-authoritative state progression to prevent scalping and seat hoarding.

> [!TIP]
> **Complete Integration & Handoff Guide**: For a detailed walkthrough on setting up your virtual environment, navigating all routes, seeding demo accounts, and testing, see [BACKEND_INTEGRATION_GUIDE.md](BACKEND_INTEGRATION_GUIDE.md).

---

## Quickstart

### 1. Create Virtual Environment
```bash
python -m venv .venv

# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
```

### 3. Environment Configuration
```bash
cp .env.example .env
```
Ensure your database connection string and Supabase credentials are configured in `.env`.

### 4. Seed Demo Accounts
```bash
python -m scripts.seed_demo_accounts
```
*Creates `admin@fairdrop.com` (`AdminPassword123!`) and `user@fairdrop.com` (`UserPassword123!`).*

### 5. Run the Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Directory Structure

```
backend/
├── app/
│   ├── api/                    # Master router and all API endpoint modules
│   │   ├── router.py           # API v1 prefix aggregator
│   │   ├── routes_admin.py     # Campaign CRUD, seat map layout, freeze, and lottery draw
│   │   ├── routes_audit.py     # Cryptographic audit trail & public verification
│   │   ├── routes_auth.py      # GoTrue JWT authentication & profile registration
│   │   ├── routes_campaigns.py # Public campaigns catalog, details, and result lookup
│   │   ├── routes_challenges.py# MediaPipe ML challenge issuance & verification
│   │   ├── routes_entitlements.py# 120s seat hold reservation (SKIP LOCKED) and claim
│   │   ├── routes_health.py    # Service health and readiness probes
│   │   ├── routes_metrics.py   # Telemetry, latencies, failure rates
│   │   └── routes_registration.py# Campaign roster registration & anti-abuse checks
│   ├── core/                   # In-memory stores (rate limiting)
│   ├── domain/                 # Domain state machines (Campaign FSM)
│   ├── integrations/           # Challenge adapters and Cloudflare Turnstile
│   ├── middleware/             # Rate limiters and security headers
│   ├── models/                 # SQLAlchemy 2.0 async database models
│   ├── repositories/           # Data access layer
│   ├── schemas/                # Pydantic v2 schemas and request contracts
│   ├── security/               # Cryptographic hashing and token verification
│   ├── services/               # Core business services
│   ├── workers/                # Background hold and entitlement expiry runners
│   ├── config.py               # Application settings
│   ├── database.py             # Async connection pool & session factory
│   ├── dependencies.py         # FastAPI dependency injection
│   └── main.py                 # FastAPI application factory
├── mediapipe_engine/           # Embedded 21-landmark geometric challenge engine
├── migrations/                 # Alembic async migration files
├── scripts/                    # Developer and operational CLI utilities
├── tests/                      # Automated test suite
├── .env.example                # Sanitized environment template
├── .gitignore                  # Git exclusion rules
├── BACKEND_INTEGRATION_GUIDE.md# Detailed developer and integration manual
├── pyproject.toml              # Build & dependency metadata
├── requirements.txt            # Runtime dependencies
└── requirements-dev.txt        # Development and testing dependencies
```

---

## Running Tests

```bash
# Complete pytest integration suite
pytest -v

# Standalone ML gesture engine tests
python handoff_bundle/test_scripts/test_mediapipe_standalone.py

# End-to-end user simulation CLI
python -m scripts.simulate_user_flow
```
