# Integration Guide — Hand-Gesture Challenges

This guide is for Dhruv. Copy the snippets, point the adapter at `mediapipe_engine`, and mount the router. No Alembic migration is required.

## 1. Copy backend files

Paste these five files into the matching paths under `app/`:

```
handoff_bundle/backend/schemas/challenge.py          →  app/schemas/challenge.py
handoff_bundle/backend/integrations/challenge_adapter.py →  app/integrations/challenge_adapter.py
handoff_bundle/backend/integrations/turnstile.py     →  app/integrations/turnstile.py
handoff_bundle/backend/services/challenge_service.py →  app/services/challenge_service.py
handoff_bundle/backend/api/routes_challenges.py      →  app/api/routes_challenges.py
```

Those files keep `from app....` imports so they drop into the existing FastAPI package.

## 2. Place the CV engine

Copy `handoff_bundle/mediapipe_engine/` to the **repository root** next to `apps/` (or next to the backend package), so this import works:

```python
from mediapipe_engine.gesture_engine import GestureEngine
```

The bundled `challenge_adapter.py` tries, in order:

1. `mediapipe_engine.gesture_engine`
2. `apps.mediapipe.gesture_engine` (Naman's original path)

Add the folder to `PYTHONPATH` if the process does not start at repo root.

## 3. Mount the router

In `app/api/router.py` (or equivalent):

```python
from app.api import routes_challenges

api_router = APIRouter(prefix="/api/v1")  # or lru_settings().API_V1_PREFIX
api_router.include_router(routes_challenges.router)
```

`routes_challenges.router` already uses `prefix="/challenges"`, so the public paths are:

- `POST /api/v1/challenges`
- `POST /api/v1/challenges/{challenge_id}/verify`
- `GET  /api/v1/challenges/metrics`

Auth, DB session, and request IDs use existing dependencies:

- `get_current_identity`
- `get_db`
- `get_request_id`

Until a sessions table exists, `user_session_id` is stubbed to `participant.id`.

## 4. Dependencies Dhruv already has vs this bundle

| Package | Who needs it |
| --- | --- |
| FastAPI, SQLAlchemy, Pydantic | Backend (already in Dhruv's app) |
| `httpx` | Turnstile live verify + integration test |
| `mediapipe`, `opencv-python`, `numpy` | Optional live Python CV; **not** required for `test_mediapipe_standalone.py` |

Install CV extras from this folder if needed:

```bash
pip install -r handoff_bundle/requirements.txt
```

Turnstile settings are read from `app.config.lru_settings()`:

- `TURNSTILE_SITEKEY`
- `TURNSTILE_SECRET_KEY`
- `APP_ENV`

Dev fallbacks are Cloudflare dummy keys inside `turnstile.py`.

## 5. Existing models the service expects (do not migrate)

`challenge_service.py` imports:

- `app.models.challenge.Challenge`
- `app.models.audit.AuditEvent`
- `app.models.audit.MetricEvent`

The service expects `Challenge` fields already used in Naman's code: `id`, `campaign_id`, `session_id`, `participant_id`, `type`, `nonce_hash`, `status`, `expires_at`, `attempt_count`, `max_attempts`, `implementation_version`, `consumed_at`, `created_at`.

If those columns exist, **do not add a migration**.

## 6. How a MEDIAPIPE challenge is issued and checked

1. Client `POST /api/v1/challenges` with `type=MEDIAPIPE`.
2. `ChallengeAdapter.get_instructions("MEDIAPIPE")` calls `GestureEngine.generate_challenge_instructions()`.
3. `implementation_version` is stored as `mediapipe-v1:{GESTURE}:{HAND}`.
4. Raw nonce is returned once; only `nonce_hash` is stored.
5. Client captures 21 landmarks / wrist trajectory and `POST .../verify`.
6. Service reconstructs `{gesture, hand}` from `implementation_version` and calls `GestureEngine.validate_submission`.
7. Geometric checks:
   - `THUMBS_UP` → 21-landmark fold/extend math
   - `SWIPE` → horizontal trajectory (6+ points)
   - `MOVE` → palm/wrist displacement (8+ points)
   - `OPEN`, `CLOSE`, `POINTER`, `OK` → client `result=SUCCESS` and `confidence >= 0.7` (no extra detector files)

Wrong `hand_used` returns `HAND_MISMATCH` and the challenge is marked `FAILED`.

## 7. Cooldown and accessibility fallback (already in the service)

- **Cooldown:** 3 `FAILED`/`EXPIRED` challenges in 300 seconds → `HTTP 429` with `COOLDOWN_ACTIVE`.
- **Fallback:** `type=MEDIAPIPE` + `fallback_requested=true` issues a `VISUAL` challenge instead. No camera, no schema change.

## 8. Smoke tests

No database:

```bash
python handoff_bundle/test_scripts/test_mediapipe_standalone.py
```

Against a running Uvicorn API:

```bash
python handoff_bundle/test_scripts/test_integration_simulated.py --token <JWT> --campaign-id <UUID>
```

## 9. Frontend

Use `frontend_integration/mediapipe_client.html` as the HUD reference. Payload field names are in `API_CONTRACT.md` and `mediapipe_client_notes.md`.
