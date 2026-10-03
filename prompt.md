You are building the backend for "Fair Drop." Steps 1–4 are complete (scaffold, DB models, Supabase JWT auth + JIT provisioning + RBAC, campaign lifecycle + state machine + seats + admin routes).

This is STEP 4.5. Create an automated integration test suite that validates everything built so far. Do NOT implement new product features. Only tests.

EXISTING STATE:
- FastAPI app at app.main:app
- Auth deps: get_current_identity, require_admin, require_verified_participant
- Campaign service + public/admin/status routes exist
- DB models and get_db() exist
- Error envelope: {"error":{"code","message","request_id","details"}}
- Python 3.11.9, pytest + pytest-asyncio + httpx already in pyproject.toml

GOAL:
Create reliable async API tests using httpx.AsyncClient + ASGITransport against the real app. Use a test database if DATABASE_URL is available; otherwise skip DB-backed tests cleanly.

--------------------------------------------------
SECTION 1: Test infrastructure
--------------------------------------------------

Create:

1) /apps/backend/tests/__init__.py
2) /apps/backend/tests/conftest.py
3) /apps/backend/tests/test_health.py
4) /apps/backend/tests/test_auth.py
5) /apps/backend/tests/test_campaigns.py
6) /apps/backend/tests/utils_auth.py

In conftest.py provide:

- pytestmark = pytest.mark.asyncio for async tests
- fixture `app` importing app.main:app
- fixture `client` = httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
- fixture `auth_header_user` and `auth_header_admin`
  - Prefer env vars:
    - TEST_USER_JWT
    - TEST_ADMIN_JWT
  - If missing, create RS/HS test JWTs ONLY if SUPABASE_JWT_SECRET is set, with claims:
    - sub: stable UUID
    - email: test user email
    - aud: settings.SUPABASE_JWT_AUDIENCE
    - role: "authenticated"
    - exp: now+1h
  - For admin tests, ensure profile.role is ADMIN in DB (seed/update profiles row), not a forged role in JWT
- fixture `request_id_header` => {"X-Request-ID": "test-req-123"}
- helper assert_error(resp, status_code, code) that checks envelope shape:
  - resp.status_code == status_code
  - body["error"]["code"] == code
  - "message" in body["error"]
  - "request_id" in body["error"]
  - "details" in body["error"]

In utils_auth.py:
- make_jwt(sub, email, secret, audience, expires_in=3600) using PyJWT HS256
- auth_headers(token, request_id=None) -> dict

IMPORTANT AUTH RULE:
- JWT proves identity only
- ADMIN authorization comes from profiles.role in DB
- Never accept admin from request body

--------------------------------------------------
SECTION 2: Health + middleware tests
--------------------------------------------------

File: tests/test_health.py

Test cases:
1. GET / returns 200 and service=fair-drop
2. GET /health returns 200 and status=healthy and timestamp present
3. X-Request-ID sent by client is echoed in response header
4. If no X-Request-ID, server still returns some x-request-id header

--------------------------------------------------
SECTION 3: Auth + RBAC tests
--------------------------------------------------

File: tests/test_auth.py

Test cases:
1. GET /api/v1/auth/me without token => 401 AUTH_REQUIRED
2. GET /api/v1/auth/me with garbage token => 401 INVALID_TOKEN (or TOKEN_DECODE_FAILED)
3. GET /api/v1/auth/me with valid user JWT => 200
   - body has profile, participant, server_time
   - profile.role == "USER" (unless that identity was seeded admin)
4. Second GET /api/v1/auth/me with same JWT => same profile.id and participant.id (JIT is idempotent)
5. GET /api/v1/auth/me/admin with user JWT => 403 FORBIDDEN
6. GET /api/v1/auth/me/admin with admin JWT (and profiles.role=ADMIN) => 200
7. Error response includes request_id from X-Request-ID when provided
8. Authorization scheme must be Bearer; malformed auth should fail safely

--------------------------------------------------
SECTION 4: Campaign lifecycle tests
--------------------------------------------------

File: tests/test_campaigns.py

Use admin auth for admin routes and user auth for status route.

Test cases:

A. Access control
1. POST /api/v1/admin/campaigns without auth => 401
2. POST /api/v1/admin/campaigns with user auth => 403 FORBIDDEN

B. Create + public visibility
3. Admin creates campaign with valid payload => 201 status=DRAFT
4. GET /api/v1/campaigns (public) does not include DRAFT campaign
5. GET /api/v1/campaigns/{id} public for DRAFT => 404
6. GET /api/v1/admin/campaigns/{id} => 200 and includes seat_counts/registration_counts

C. Validation
7. Create campaign with registration_end <= registration_start => 422
8. Create campaign with capacity <= 0 => 422

D. Edit rules
9. PATCH draft campaign name => 200
10. After OPEN, PATCH should return 409 CAMPAIGN_NOT_EDITABLE

E. State machine happy path
For timestamps: set registration_start to now-1min, registration_end now+1h, redemption_deadline now+2h so publish works.

11. POST /prepare => PREPARING and seats generated (seat_counts.total == capacity, available == capacity)
12. POST /prepare again => 409 INVALID_STATE_TRANSITION
13. POST /publish => OPEN and published_at/policy_hash set
14. Public list includes campaign
15. Public get by id returns 200
16. POST /close => CLOSED
17. POST /freeze => FROZEN
18. POST /draw => DRAWING (placeholder behavior from Step 4 is fine)

F. Invalid transitions
19. close on FROZEN => 409 INVALID_STATE_TRANSITION
20. freeze on OPEN => 409 INVALID_STATE_TRANSITION

G. Pause/resume
21. pause REGISTRATION => registration_paused true
22. resume REGISTRATION => registration_paused false
23. pause ADMISSION and REDEMPTION both toggle correctly

H. Status recovery endpoint
24. GET /api/v1/campaigns/{id}/status without auth => 401
25. GET /api/v1/campaigns/{id}/status with user auth => 200
    - participant_state == "NOT_REGISTERED"
    - registration is null
    - campaign.server_time present

I. Audit trail smoke check
26. After create/prepare/publish, at least one audit-related behavior is observable
   - Prefer DB check if easy via session
   - If not, at least ensure transition endpoints return previous_status/new_status correctly

--------------------------------------------------
SECTION 5: Pytest config
--------------------------------------------------

Update pyproject.toml or add pytest.ini:

- asyncio_mode = auto
- testpaths = ["tests"]
- pythonpath = ["."]

Add a short tests section in /apps/backend/README.md:

```bash
# optional real JWTs
export TEST_USER_JWT=...
export TEST_ADMIN_JWT=...

pytest -q