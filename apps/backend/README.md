# Fair Drop — Backend

Fair Drop is a high-demand event seat allocation platform designed to ensure fair, transparent, and bot-resistant ticket distribution. The platform integrates cryptographically signed permits, fair queue mechanics, and strict server-authoritative state progression to prevent scalping and seat hoarding.

## Python Requirement

- **Python Version**: `>=3.11.9, <3.12` (Strict requirement: **3.11.9**)

## Setup

1. **Verify Python version**:
   ```bash
   python --version
   # Expected: Python 3.11.9
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   ```

3. **Activate virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     source .venv/bin/activate
     ```

4. **Upgrade pip**:
   ```bash
   python -m pip install --upgrade pip
   ```

5. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

6. **Configure environment**:
   ```bash
   # Copy example environment configuration
   cp .env.example .env
   ```
   Edit `.env` to verify or provide your configuration values (e.g., database connection, Supabase secrets).

## Running the Application

From `/apps/backend/`, run:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Available Endpoints (Step 1 Shell)

- `GET /` — Service status check (`{"service": "fair-drop", "status": "running", "version": "0.1.0"}`)
- `GET /health` — Health check endpoint (`{"status": "healthy", "timestamp": "<ISO UTC>"}`)
- `GET /docs` — Swagger OpenAPI interactive documentation
- `GET /redoc` — ReDoc interactive API documentation

## Code Quality and Linting

- **Check linting**:
  ```bash
  ruff check .
  ```
- **Format code**:
  ```bash
  ruff format .
  ```

## Running Tests

Run the automated integration test suite:

```bash
# Optional: supply real external Supabase JWTs (otherwise mock HS256 tokens are signed automatically)
export TEST_USER_JWT=...
export TEST_ADMIN_JWT=...

# Run the complete test suite
pytest -q

# Or run with verbose per-test reporting
pytest -v
```

## Directory Structure

```
apps/backend/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── app/
    ├── __init__.py
    ├── config.py
    ├── main.py
    ├── api/
    │   ├── __init__.py
    │   └── router.py
    ├── domain/
    │   └── __init__.py
    ├── models/
    │   └── __init__.py
    ├── schemas/
    │   └── __init__.py
    ├── repositories/
    │   └── __init__.py
    ├── services/
    │   └── __init__.py
    ├── security/
    │   └── __init__.py
    ├── integrations/
    │   └── __init__.py
    └── workers/
        └── __init__.py
```
