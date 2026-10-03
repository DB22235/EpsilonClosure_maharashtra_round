# Naman — Role Context

## Role

You own the **MediaPipe human-validation and challenge pipeline** for Fair Drop. Your work is an anti-abuse friction layer, not a claim of perfect bot detection.

## Project understanding

Fair Drop must distribute 500 seats fairly among a very large participant population. The system does not promise to identify every bot. It must prevent automation from gaining extra chances through speed, request volume, repeated attempts, token replay, or queue manipulation.

Your pipeline is used when the backend decides that a session needs step-up friction, especially before final entitlement redemption or after suspicious repeated behavior.

## Primary responsibilities

- Use Python **3.11.9**.
- Create `/apps/mediapipe/.venv` using Python 3.11.9.
- Implement the MediaPipe hand/gesture challenge pipeline.
- Implement five small challenges:
  1. Open palm.
  2. Thumbs-up.
  3. Thumbs-down.
  4. Two fingers.
  5. Hold a hand inside a target region.
- Keep challenges short, approximately 5–10 seconds.
- Generate a clear challenge instruction and timer.
- Bind every challenge to a fresh nonce and session.
- Ensure a challenge can be accepted only once and expires quickly.
- Provide an accessibility-friendly alternative for users who cannot or do not want to use a camera.
- Document the result contract that Dhruv’s backend can consume.
- Add local tests for gesture recognition, expiry, malformed results, and replay.
- Provide screenshots or a short capture for the final demo if useful.

## Do not own

Do not modify:

- FastAPI route implementation.
- PostgreSQL migrations.
- Seat allocation logic.
- Lottery logic.
- Frontend application screens outside the challenge component/contract.
- Dhanya’s simulator.

If backend integration is required, expose a documented adapter or HTTP-friendly result. Dhruv should integrate the adapter rather than importing your internal implementation.

## Recommended directory ownership

```text
/apps/mediapipe/
  README.md
  requirements.txt or pyproject.toml
  src/
    challenge_engine/
    gestures/
    challenge_contract.py
    local_runner.py
  tests/
  examples/
```

## Required result contract

The backend should receive a result conceptually like:

```json
{
  "challenge_id": "ch_123",
  "session_id": "sess_123",
  "campaign_id": "camp_123",
  "nonce": "fresh-client-result-nonce",
  "challenge_type": "OPEN_PALM",
  "result": "PASS",
  "confidence": 0.93,
  "duration_ms": 7200,
  "client_timestamp": "optional",
  "implementation_version": "mediapipe-v1"
}
```

The backend must not trust the browser result alone. It should validate challenge existence, session binding, nonce, expiry, attempt count, and server-side policy. Your contract must therefore make those fields available but should not attempt to enforce backend authority inside the CV code.

## Challenge design requirements

Each challenge must:

- Display one instruction at a time.
- Use a short server-issued challenge nonce.
- Have a timeout.
- Produce PASS, FAIL, or ABANDONED.
- Avoid exposing the expected answer in a way a trivial script can read.
- Be accepted only once by the backend.
- Avoid requiring a perfect camera or lighting condition.
- Have a fallback path.

MediaPipe output is a risk/friction signal. Do not describe it as proof that a user is human.

## Accessibility and false positives

Do not automatically reject users because of:

- Poor lighting.
- Slow network.
- Keyboard-only operation.
- Assistive technology.
- A shared device.
- A camera that is unavailable.

Provide an alternative such as a visual challenge, text-based challenge, or explicit fallback flow controlled by the backend policy.

Record useful outcomes for Dhanya’s metrics:

- Challenge started.
- Challenge passed.
- Challenge failed.
- Challenge abandoned.
- Challenge timed out.
- Fallback selected.
- False-positive report if the test harness can identify it.

## Integration contract with Dhruv

Agree on these fields before implementation:

- `challenge_id`
- `session_id`
- `campaign_id`
- `challenge_type`
- `nonce`
- `result`
- `confidence`
- `attempt_count`
- `expires_at`
- `implementation_version`

Dhruv owns the final API and database representation. You own the challenge engine and its documented output.

## Integration contract with Rohan

Rohan should be able to host your challenge through a stable component or HTTP contract. Provide:

- Start challenge input.
- Instruction and timer output.
- Camera permission failure state.
- Progress state.
- Success/failure/timeout events.
- Accessibility fallback event.

Do not require Rohan to know MediaPipe internals.

## Integration contract with Dhanya

Dhanya should be able to test:

- Challenge success.
- Challenge failure.
- Timeout.
- Replay of a passed challenge.
- Reuse of a nonce.
- Repeated failed challenges.
- Fallback use.

Provide a mock mode for deterministic tests. The simulator must not need a real camera for every load test.

## Python environment

```bash
cd /path/to/repository/apps/mediapipe
python3.11 --version   # must be 3.11.9
python3.11 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
```

Commit dependency files. Do not commit `.venv`.

## Definition of done

- Five challenges exist or the first challenge is fully reliable with the remaining four clearly stubbed and documented.
- Every challenge has timeout, nonce, one-time-use, and fallback behavior.
- Result contract is documented.
- Local deterministic tests pass.
- Backend integration does not depend on internal MediaPipe imports.
- No claims are made that the challenge perfectly identifies humans.
- Files remain inside `/apps/mediapipe` except for shared API documentation changes agreed with Dhruv.
