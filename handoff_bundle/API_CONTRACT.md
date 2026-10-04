# API Contract — Challenges

Base path: `/api/v1`  
Router prefix: `/challenges`  
Auth: bearer identity (`get_current_identity`) on all routes below.

## POST `/api/v1/challenges`

Creates a proof-of-human challenge. Returns the **raw nonce once**.

### Request

```json
{
  "campaign_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "type": "MEDIAPIPE",
  "operation": "REGISTER",
  "requested_reason": "MEDIUM_RISK",
  "fallback_requested": false,
  "accessibility_reason": null
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `campaign_id` | UUID | Required |
| `type` | `TURNSTILE` \| `MEDIAPIPE` \| `VISUAL` \| `MOCK` | Required |
| `operation` | string | e.g. `REGISTER`, `REDEEM` |
| `requested_reason` | string | e.g. `MEDIUM_RISK` |
| `fallback_requested` | bool | default `false`; if `true` with `MEDIAPIPE`, issued type becomes `VISUAL` |
| `accessibility_reason` | string \| null | e.g. `CAMERA_DENIED` |

### Success `201`

```json
{
  "challenge_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "type": "MEDIAPIPE",
  "status": "PENDING",
  "nonce": "a1b2c3d4e5f67890123456789abcdef0",
  "expires_at": "2026-10-04T00:10:00Z",
  "max_attempts": 2,
  "implementation_version": "mediapipe-v1:THUMBS_UP:LEFT",
  "instructions": {
    "gesture": "THUMBS_UP",
    "hand": "LEFT",
    "prep_time_seconds": 2.0,
    "time_limit_seconds": 6.0,
    "gesture_hold_seconds": 0.6,
    "instruction_text": "[LEFT] Make a THUMBS UP gesture with your LEFT hand"
  }
}
```

MediaPipe `implementation_version` format: `mediapipe-v1:{GESTURE}:{HAND}`.

## POST `/api/v1/challenges/{challenge_id}/verify`

### Headers

| Header | Required | Notes |
| --- | --- | --- |
| `Authorization` | yes | Bearer token |
| `Idempotency-Key` | no | Passed through to audit metadata |

### Request

```json
{
  "nonce": "a1b2c3d4e5f67890123456789abcdef0",
  "type": "MEDIAPIPE",
  "result": "SUCCESS",
  "confidence": 0.92,
  "duration_ms": 2150,
  "implementation_version": "mediapipe-v1:THUMBS_UP:LEFT",
  "turnstile_token": null,
  "hand_used": "LEFT",
  "model_metadata": {
    "landmarks": [[500.0, 700.0], "... 21 points ..."],
    "trajectory": [[500.0, 700.0], [520.0, 698.0]]
  }
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `nonce` | string | Must hash-match stored `nonce_hash` |
| `type` | enum | Same family as issued challenge |
| `result` | `SUCCESS` \| `FAILURE` | Client-side outcome |
| `confidence` | float 0..1 \| null | Geometric pass also requires `>= 0.7` |
| `duration_ms` | int `>= 0` | Used for risk scoring (`< 800` → HIGH) |
| `implementation_version` | string | Echo issued version |
| `turnstile_token` | string \| null | Turnstile only |
| `hand_used` | `LEFT` \| `RIGHT` \| null | Mismatch → `HAND_MISMATCH` |
| `model_metadata.landmarks` | `list[list[float]]` | 21 MediaPipe hand points `[x, y]` or `[x, y, z]` |
| `model_metadata.trajectory` | `list[list[float]]` | Wrist/palm history; alias `point_history` |

### Success `200`

```json
{
  "challenge_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "PASSED",
  "risk_level": "LOW",
  "reason_code": "CHALLENGE_PASSED",
  "verified_until": "2026-10-04T00:15:00Z"
}
```

`status` may be `PASSED` or `FAILED`. Failed geometric / hand checks still return `200` with `status=FAILED` (not an HTTP error).

## GET `/api/v1/challenges/metrics`

Query: optional `campaign_id`. Returns aggregated pass/fail/abandon rates, latency, fallback count, cooldown triggers, and per-type breakdown.

## Error envelope

HTTP errors use:

```json
{
  "error": {
    "code": "COOLDOWN_ACTIVE",
    "message": "Too many failed attempts. Cooldown active.",
    "request_id": "...",
    "details": {
      "retry_after_seconds": 280,
      "cooldown_expires_at": "2026-10-04T00:20:00+00:00"
    }
  }
}
```

| HTTP | `error.code` | When |
| --- | --- | --- |
| 429 | `COOLDOWN_ACTIVE` | ≥ 3 FAILED/EXPIRED in 300s |
| 404 | `CHALLENGE_NOT_FOUND` | Unknown id |
| 403 | `CHALLENGE_SESSION_MISMATCH` | Identity session ≠ challenge session |
| 409 | `CHALLENGE_REPLAYED` | Status is not `PENDING` |
| 403 | `CHALLENGE_NONCE_MISMATCH` | Nonce hash mismatch |
| 410 | `CHALLENGE_EXPIRED` | Past `expires_at` |
| 429 | `CHALLENGE_ATTEMPT_LIMIT` | `attempt_count > max_attempts` (default 2) |
| 422 | validation | Pydantic body errors |

## Verify reason codes (`reason_code`)

| Code | Meaning |
| --- | --- |
| `CHALLENGE_PASSED` | Geometric or fallback validation succeeded (may be overwritten by risk scoring) |
| `HAND_MISMATCH` | `hand_used` ≠ instructed hand |
| `GEOMETRIC_VALIDATION_FAILED` | Landmarks/trajectory failed detector |
| `LOW_CONFIDENCE` | Confidence below 0.7 |
| `CHALLENGE_FAILED` | Generic failure |
| `TURNSTILE_VALIDATION_FAILED` | Turnstile token rejected |
| `TELEMETRY_ANOMALY_TOO_FAST` | Passed adapter but `duration_ms < 800` → `risk_level=HIGH` |
| `TELEMETRY_ANOMALY_TOO_SLOW` | `duration_ms > 15000` → `MEDIUM` |
| `REPEATED_ATTEMPTS` | `attempt_count > 1` on a pass → `MEDIUM` |

Risk scoring runs **only after** adapter pass and may replace `reason_code`.
