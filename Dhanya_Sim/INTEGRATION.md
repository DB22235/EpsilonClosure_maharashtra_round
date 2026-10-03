# Fair Drop Simulator — Integration Guide

## For Rohan (Frontend)
- Consume: `Dhanya_Sim/output/dashboard_feed.json`
- Schema version: 1.0 (field `schema_version`)
- Regenerate anytime: `python3 -m Dhanya_Sim.runner.engine --generate-demo-assets --mock-mode`
- Live data regen (when Dhruv's backend is up): add `--live` flag

## For Dhruv (Backend)
- Simulator hits these endpoints (all documented in Universal Context §9):
  POST /api/campaigns/{id}/join
  POST /api/campaigns/{id}/register
  GET  /api/campaigns/{id}/status
  POST /api/challenges, POST /api/challenges/{id}/verify
  POST /api/entitlements/{id}/hold, redeem, release
  GET  /api/campaigns/{id}/result, /audit, /metrics
- Simulator expects error shape: `{"error": {"code": "...", "message": "...", "request_id": "..."}}`
- Simulator sends `Idempotency-Key` header on all mutating requests
- Health check endpoint: `/health` or `/api/health`

## For Naman (MediaPipe)
- Simulator uses mock challenge responses in bulk load tests.
- No MediaPipe internals imported.
- Challenge adapter contract: POST /api/challenges returns `{challenge_id, nonce, type}`
  POST /api/challenges/{id}/verify accepts `{nonce, answer}` returns `{status, risk_delta}`

## Running the Simulator
- Mock mode (standalone, no backend needed):
  `python3 -m Dhanya_Sim.runner.engine --generate-demo-assets --mock-mode`
- Live mode (requires Dhruv's backend running):
  `python3 -m Dhanya_Sim.runner.engine --scenario 15 --live --base-url http://localhost:8000`
- Full test suite:
  `python3 tests/simulation/test_adversarial_suite.py`
- Full demo rehearsal:
  `./Dhanya_Sim/demo_rehearsal.sh`

## Owned Directories
- `/Dhanya_Sim/` (all simulator code, configs, outputs)
- `/tests/simulation/` (test suite + run reports)
