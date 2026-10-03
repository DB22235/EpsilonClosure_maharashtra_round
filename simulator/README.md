# Fair Drop Live Adversarial Simulator

The Live Adversarial Simulator generates real, authenticated traffic against Dhruv's FastAPI backend and Supabase instance. It benchmarks system integrity, bot mitigation, and lottery fairness under adversarial conditions.

---

## Architecture & Layout

```
simulator/
├── .env.example              # Environment variables template
├── .gitignore
├── requirements.txt          # Python dependencies
├── config.py                 # Pydantic settings loading .env
├── runner.py                 # CLI entrypoint for scenarios
├── fixtures/
│   ├── __init__.py
│   └── seed_users.py         # Provision 100 test accounts in Supabase
├── metrics/
│   ├── __init__.py
│   ├── collector.py          # Real-time HTTP request & latency collector
│   ├── analyzer.py           # Fairness, integrity assertions & percentiles
│   └── reporter.py           # Outputs JSON, CSV, and Markdown judge reports
├── profiles/                 # 8 Adversarial and Human behavior profiles
│   ├── __init__.py
│   ├── base.py               # Abstract base client with auth/metrics hooks
│   ├── normal_human.py       # Baseline human client with realistic jitter
│   ├── fast_bot.py           # High-speed bot skipping permits then retrying
│   ├── burst_bot.py          # Parallel burst registrations with identical Idempotency-Key
│   ├── retry_bot.py          # Sequential retries with identical Idempotency-Key
│   ├── direct_api_bot.py     # Unpermitted direct register call attacker
│   ├── token_replay.py       # Replay attacker reusing permit across fresh keys
│   ├── race_attacker.py      # High-concurrency race attacker on entitlement /hold
│   └── shared_network.py     # Distinct NAT/IP fingerprint normal human
├── reports/                  # Generated JSON, CSV, and MD presentation reports
│   ├── .gitkeep
│   └── latest.json           # Symlinked/Latest scenario snapshot for dashboards
└── scenarios/                # 6 Adversarial test scenarios
    ├── __init__.py
    ├── admin_helper.py       # Campaign creation and lottery draw helpers
    ├── s01_baseline.py       # 50 Humans, 50 Capacity
    ├── s02_bot_flood.py      # 20 Humans vs 80 Bots (The Money Shot)
    ├── s03_replay_attack.py  # Permit replay vulnerability test
    ├── s04_race_condition.py # Entitlement claim race attack
    ├── s05_full_adversarial.py # Chaotic 8-profile concurrent mix
    └── s06_cutoff_boundary.py  # Precise cutoff timestamp enforcement
```

---

## Getting Started

### 1. Environment Setup

```bash
cd simulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Credentials

Copy `.env.example` to `.env` and fill in the Supabase and Backend values:

```bash
cp .env.example .env
```

Required keys in `.env`:
- `BACKEND_URL`: URL of the FastAPI backend (e.g., `http://localhost:8000`)
- `SUPABASE_URL`: Supabase project URL (e.g., `https://xyz.supabase.co`)
- `SUPABASE_ANON_KEY`: Supabase anon public key
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key for admin user creation
- `ADMIN_EMAIL`: Admin email for lottery operations
- `ADMIN_PASSWORD`: Admin password

### 3. Seed Users

To pre-seed 100 test user accounts with valid Supabase JWTs:

```bash
python -m simulator.runner --seed
```

This writes user credentials and JWTs to `simulator/fixtures/seeded_users.json`.

---

## Running Scenarios

List all available scenarios:
```bash
python -m simulator.runner --list
```

Run a specific scenario (e.g. S02 Bot Flood):
```bash
python -m simulator.runner --scenario s02
```

Run all 6 scenarios sequentially:
```bash
python -m simulator.runner --all
```

---

## Reports & Frontend Integration

Every scenario run generates three artifacts in `simulator/reports/`:
- `{scenario}_{timestamp}.json`: Full statistical summary including latencies and win rates.
- `latest.json`: Mirrored copy of the latest run, directly consumable by Rohan's frontend dashboard.
- `{scenario}_{timestamp}.csv`: Complete log of every HTTP request, status, and latency.
- `{scenario}_{timestamp}.md`: Formatted judge presentation summary with PASS/FAIL assertion tables.
