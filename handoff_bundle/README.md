# Hand-Gesture Verification Handoff Bundle

This folder is a self-contained drop for Dhruv to wire Naman's MediaPipe challenge engine into the Fair Drop backend.

It contains **only** the CV engine, challenge integration snippets, a browser client example, and docs. It does **not** include database migrations, models, datasets, or the rest of the core backend.

## Why no DB schema / migration changes are needed

Challenge persistence already uses the existing `Challenge` table plus `AuditEvent` / `MetricEvent`. Issuance, nonce hashing, cooldown, and verification all write to those tables. Dropping in these files does not add columns, tables, or Alembic revisions.

## Layout

```
handoff_bundle/
├── README.md
├── INTEGRATION_GUIDE.md
├── API_CONTRACT.md
├── requirements.txt
├── backend/                  # paste into Dhruv's app package
├── mediapipe_engine/         # self-contained CV package
├── frontend_integration/
└── test_scripts/
```

## Install (CV / test scripts only)

From this folder:

```bash
pip install -r requirements.txt
```

`mediapipe_engine` itself uses only the Python standard library plus the geometric math in `detectors/`. `mediapipe` and `opencv-python` are for a live camera Python client if you add one later. The standalone unit test does **not** need a webcam, Uvicorn, or PostgreSQL.

## Run the standalone CV test (no backend)

From the **repository root** (parent of `handoff_bundle/`):

```bash
python handoff_bundle/test_scripts/test_mediapipe_standalone.py
```

Expected last line:

```text
[PASS] Standalone MediaPipe Engine Test Completed Successfully
```

## Run the simulated API integration test

Requires Dhruv's FastAPI app on Uvicorn, a bearer token, and a campaign UUID:

```bash
python handoff_bundle/test_scripts/test_integration_simulated.py --token <JWT> --campaign-id <UUID>
```

Optional: `--base-url http://127.0.0.1:8000/api/v1/`

## Where to paste files

See `INTEGRATION_GUIDE.md`. Short version:

| Bundle file | Destination in Dhruv's backend |
| --- | --- |
| `backend/schemas/challenge.py` | `app/schemas/challenge.py` |
| `backend/integrations/challenge_adapter.py` | `app/integrations/challenge_adapter.py` |
| `backend/integrations/turnstile.py` | `app/integrations/turnstile.py` |
| `backend/services/challenge_service.py` | `app/services/challenge_service.py` |
| `backend/api/routes_challenges.py` | `app/api/routes_challenges.py` |
| `mediapipe_engine/` | repo root (or add that folder to `PYTHONPATH`) |

Then mount the challenges router on `/api/v1` if it is not already included.

## Browser HUD

Open `frontend_integration/mediapipe_client.html` in a browser with camera permission. Landmark JSON shape is documented in `frontend_integration/mediapipe_client_notes.md`.
