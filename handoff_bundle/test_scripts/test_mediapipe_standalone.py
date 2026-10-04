"""
Standalone MediaPipe GestureEngine tests. No Uvicorn, no PostgreSQL, no webcam.
"""

from __future__ import annotations

import sys
from pathlib import Path

BUNDLE_ROOT = Path(__file__).resolve().parents[1]
if str(BUNDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(BUNDLE_ROOT))

from mediapipe_engine.detectors.move_detector import is_valid_move
from mediapipe_engine.detectors.swipe_detector import is_valid_swipe
from mediapipe_engine.detectors.thumbs_up_detector import is_thumbs_up
from mediapipe_engine.gesture_engine import GestureEngine
from mediapipe_engine.verifier import GestureVerifier


def generate_mock_landmarks_for_thumbs_up() -> list[list[float]]:
    landmarks = [[500.0, 700.0] for _ in range(21)]
    landmarks[0] = [500.0, 700.0]
    landmarks[2] = [450.0, 600.0]
    landmarks[3] = [430.0, 480.0]
    landmarks[4] = [400.0, 320.0]
    landmarks[5] = [520.0, 580.0]
    landmarks[6] = [530.0, 620.0]
    landmarks[8] = [535.0, 650.0]
    landmarks[10] = [570.0, 620.0]
    landmarks[12] = [575.0, 650.0]
    landmarks[14] = [610.0, 620.0]
    landmarks[16] = [615.0, 650.0]
    landmarks[18] = [650.0, 620.0]
    landmarks[20] = [655.0, 650.0]
    return landmarks


def generate_horizontal_swipe(n: int = 12) -> list[list[float]]:
    return [[100.0 + i * 40.0, 400.0] for i in range(n)]


def generate_move_path(n: int = 12) -> list[list[float]]:
    return [[200.0 + i * 20.0, 300.0 + i * 15.0] for i in range(n)]


def assert_true(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)
    print(f"[OK] {message}")


def main() -> int:
    instructions = GestureEngine.generate_challenge_instructions()
    required = {"gesture", "hand", "prep_time_seconds", "time_limit_seconds", "gesture_hold_seconds", "instruction_text"}
    assert_true(required.issubset(instructions.keys()), "generate_challenge_instructions returns expected keys")
    assert_true(instructions["gesture"] in GestureEngine.STATIC_GESTURES + GestureEngine.DYNAMIC_GESTURES, "gesture is supported")
    assert_true(instructions["hand"] in ("LEFT", "RIGHT"), "hand is LEFT or RIGHT")

    thumbs = generate_mock_landmarks_for_thumbs_up()
    assert_true(is_thumbs_up(thumbs), "thumbs-up geometric detector accepts synthetic pose")

    passed, conf, reason = GestureEngine.validate_submission(
        {"gesture": "THUMBS_UP", "hand": "LEFT"},
        {
            "hand_used": "LEFT",
            "confidence": 0.95,
            "result": "SUCCESS",
            "model_metadata": {"landmarks": thumbs},
        },
    )
    assert_true(passed and reason == "CHALLENGE_PASSED" and conf == 0.95, "THUMBS_UP submission validates")

    passed, _conf, reason = GestureEngine.validate_submission(
        {"gesture": "THUMBS_UP", "hand": "LEFT"},
        {
            "hand_used": "RIGHT",
            "confidence": 0.99,
            "result": "SUCCESS",
            "model_metadata": {"landmarks": thumbs},
        },
    )
    assert_true((not passed) and reason == "HAND_MISMATCH", "wrong hand is rejected")

    swipe = generate_horizontal_swipe()
    assert_true(is_valid_swipe(swipe), "swipe detector accepts horizontal trajectory")
    passed, _conf, reason = GestureEngine.validate_submission(
        {"gesture": "SWIPE", "hand": "RIGHT"},
        {
            "hand_used": "RIGHT",
            "confidence": 0.9,
            "result": "SUCCESS",
            "model_metadata": {"trajectory": swipe},
        },
    )
    assert_true(passed and reason == "CHALLENGE_PASSED", "SWIPE submission validates")

    move = generate_move_path()
    assert_true(is_valid_move(move), "move detector accepts palm displacement")
    passed, _conf, reason = GestureEngine.validate_submission(
        {"gesture": "MOVE", "hand": "LEFT"},
        {
            "hand_used": "LEFT",
            "confidence": 0.88,
            "result": "SUCCESS",
            "model_metadata": {"point_history": move},
        },
    )
    assert_true(passed and reason == "CHALLENGE_PASSED", "MOVE submission validates via point_history alias")

    for gesture in ("OPEN", "CLOSE", "POINTER", "OK"):
        passed, _conf, reason = GestureEngine.validate_submission(
            {"gesture": gesture, "hand": "LEFT"},
            {
                "hand_used": "LEFT",
                "confidence": 0.8,
                "result": "SUCCESS",
                "model_metadata": {"landmarks": thumbs},
            },
        )
        assert_true(passed and reason == "CHALLENGE_PASSED", f"{gesture} client-success path validates")

    verifier = GestureVerifier(target_gesture="THUMBS_UP", required_hand="LEFT")
    frame = verifier.process_frame("THUMBS_UP", 0.9, "LEFT", thumbs)
    assert_true(frame["verified"] is True, "GestureVerifier accepts matching thumbs-up frame")
    mismatch = verifier.process_frame("THUMBS_UP", 0.9, "RIGHT", thumbs)
    assert_true(mismatch["reason"] == "HAND_MISMATCH", "GestureVerifier rejects hand mismatch")

    print("[PASS] Standalone MediaPipe Engine Test Completed Successfully")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1)
