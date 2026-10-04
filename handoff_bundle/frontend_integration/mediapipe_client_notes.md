# MediaPipe client notes — serializing 21 hand landmarks

Supported gestures: `THUMBS_UP`, `SWIPE`, `MOVE`, `OPEN`, `CLOSE`, `POINTER`, `OK`.

Hands: `LEFT`, `RIGHT` (50/50 at issue time).

## Verify endpoint

`POST /api/v1/challenges/{challenge_id}/verify`

Send JSON that matches `ChallengeVerifyRequest`. Always include the issued `nonce` and echo `implementation_version`.

## `model_metadata` shape

```json
{
  "landmarks": [
    [0.51, 0.72, 0.0],
    [0.50, 0.68, 0.01]
  ],
  "trajectory": [
    [0.51, 0.72],
    [0.55, 0.71]
  ],
  "point_history": [
    [0.51, 0.72]
  ],
  "gesture": "THUMBS_UP",
  "hand": "LEFT"
}
```

| Key | Required for | Format |
| --- | --- | --- |
| `landmarks` | `THUMBS_UP` (and useful for all static poses) | Length **21**. Each point is `[x, y]` or `[x, y, z]`. Index 0 is wrist. MediaPipe Hands order. |
| `trajectory` | `SWIPE`, `MOVE` | Time-ordered wrist (or palm-center) points. Alias: `point_history`. |
| `gesture` / `hand` | optional | HUD bookkeeping; server reconstructs required gesture/hand from `implementation_version`. |

Coordinates may be **normalized 0..1** (browser MediaPipe) or **pixel** (OpenCV). Detectors scale swipe/move thresholds when `max(x,y) <= 1.0`.

## Mapping MediaPipe Hands JS → payload

`Hands` `onResults` gives `multiHandLandmarks[0]` (21 `{x,y,z}`) and `multiHandedness[0].label` (`Left` / `Right`).

```javascript
const landmarks = results.multiHandLandmarks[0].map((p) => [p.x, p.y, p.z]);
const handUsed = results.multiHandedness[0].label.toUpperCase(); // LEFT | RIGHT
const wrist = landmarks[0];
trajectory.push([wrist[0], wrist[1]]);
```

Keep a rolling trajectory (about 32 frames is enough for swipe). Cap length so the payload stays small.

Also set top-level fields:

- `hand_used`: same as handedness label, uppercased. Wrong hand → `HAND_MISMATCH`.
- `result`: `"SUCCESS"` if the HUD believes the pose matched, else `"FAILURE"`.
- `confidence`: `0.0`–`1.0`. Geometric pass still requires `>= 0.7`.
- `duration_ms`: elapsed since challenge start. Values under 800 ms are scored `HIGH` / `TELEMETRY_ANOMALY_TOO_FAST` even on a geometric pass.

## Gesture-specific HUD behavior

| Gesture | Client should send | Server check |
| --- | --- | --- |
| `THUMBS_UP` | 21 `landmarks` | Folded index/middle/ring/pinky; thumb tip above IP/MCP |
| `SWIPE` | `trajectory` (≥ 6 non-zero points) | Mostly horizontal displacement |
| `MOVE` | `trajectory` (≥ 8 non-zero points) | Palm/wrist travel + average step |
| `OPEN` `CLOSE` `POINTER` `OK` | `result` + `confidence` (landmarks optional) | `result === SUCCESS` and `confidence >= 0.7` |

Instruction copy from the engine looks like:

`[LEFT] Make a THUMBS UP gesture with your LEFT hand`

The example HTML page also shows: `Show your [LEFT] hand with THUMBS UP`.

## Minimum body example

```json
{
  "nonce": "<from create response>",
  "type": "MEDIAPIPE",
  "result": "SUCCESS",
  "confidence": 1.0,
  "duration_ms": 2150,
  "implementation_version": "mediapipe-v1:THUMBS_UP:LEFT",
  "hand_used": "LEFT",
  "model_metadata": {
    "landmarks": [],
    "trajectory": []
  }
}
```

Fill `landmarks` / `trajectory` from the camera loop before POST.
