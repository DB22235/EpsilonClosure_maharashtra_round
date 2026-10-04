"""
Gesture Engine for MediaPipe challenge generation and verification.
"""

from __future__ import annotations
import random
from typing import Any

from .detectors.thumbs_up_detector import is_thumbs_up
from .detectors.swipe_detector import is_valid_swipe
from .detectors.move_detector import is_valid_move


class GestureEngine:
    """
    Core engine managing MediaPipe gesture challenge generation and verification logic.
    """

    STATIC_GESTURES = ["OPEN", "CLOSE", "POINTER", "OK", "THUMBS_UP"]
    DYNAMIC_GESTURES = ["SWIPE", "MOVE"]

    @classmethod
    def generate_challenge_instructions(cls) -> dict[str, Any]:
        """
        Generates challenge instructions according to probabilistic rules:
        - 60% Static, 40% Dynamic
        - Static: 40% THUMBS_UP, 60% split across OPEN, CLOSE, POINTER, OK
        - Dynamic: 70% SWIPE, 30% MOVE
        - Hand: 50% LEFT, 50% RIGHT
        """
        # Select hand
        hand = "LEFT" if random.random() < 0.5 else "RIGHT"

        # Select category: 60% Static, 40% Dynamic
        if random.random() < 0.6:
            # Static
            if random.random() < 0.4:
                gesture = "THUMBS_UP"
            else:
                gesture = random.choice(["OPEN", "CLOSE", "POINTER", "OK"])
            hold_time = 0.6
        else:
            # Dynamic
            if random.random() < 0.7:
                gesture = "SWIPE"
            else:
                gesture = "MOVE"
            hold_time = 0.4

        # Friendly instruction text formatting
        friendly_names = {
            "THUMBS_UP": "THUMBS UP",
            "OPEN": "OPEN PALM",
            "CLOSE": "CLOSED FIST",
            "POINTER": "POINTING FINGER",
            "OK": "OK SIGN",
            "SWIPE": "SWIPE HORIZONTALLY",
            "MOVE": "MOVE HAND IN SPACE",
        }
        text_name = friendly_names.get(gesture, gesture)
        instruction_text = f"[{hand}] Make a {text_name} gesture with your {hand} hand"

        return {
            "gesture": gesture,
            "hand": hand,
            "prep_time_seconds": 2.0,
            "time_limit_seconds": 6.0,
            "gesture_hold_seconds": hold_time,
            "instruction_text": instruction_text,
        }

    @classmethod
    def validate_submission(
        cls,
        instructions: dict[str, Any],
        verify_request: Any,
    ) -> tuple[bool, float, str]:
        """
        Validates client submission against challenge instructions.
        Returns tuple of: (passed: bool, confidence: float, reason: str)
        """
        # Extract attributes from Pydantic model or dict
        if isinstance(verify_request, dict):
            hand_used = str(verify_request.get("hand_used", "")).upper()
            confidence = float(verify_request.get("confidence", 0.0))
            result = str(verify_request.get("result", "")).upper()
            model_metadata = verify_request.get("model_metadata") or {}
        else:
            hand_used = str(getattr(verify_request, "hand_used", "")).upper()
            confidence = float(getattr(verify_request, "confidence", 0.0))
            result = str(getattr(verify_request, "result", "")).upper()
            model_metadata = getattr(verify_request, "model_metadata", None) or {}

        required_hand = str(instructions.get("hand", "")).upper()
        required_gesture = str(instructions.get("gesture", "")).upper()

        # 1. Enforce hand match
        if hand_used and required_hand and hand_used != required_hand:
            return (False, 0.0, "HAND_MISMATCH")

        # Extract landmarks / trajectory if present
        landmarks = model_metadata.get("landmarks") or []
        trajectory = model_metadata.get("trajectory") or model_metadata.get("point_history") or []

        # 2. Geometric evaluation if raw telemetry available
        if landmarks or trajectory:
            geom_passed = False
            if required_gesture == "THUMBS_UP" and landmarks:
                geom_passed = is_thumbs_up(landmarks)
            elif required_gesture == "SWIPE" and trajectory:
                geom_passed = is_valid_swipe(trajectory)
            elif required_gesture == "MOVE" and trajectory:
                geom_passed = is_valid_move(trajectory)
            else:
                # Other static/fallback gestures (OPEN, CLOSE, POINTER, OK)
                geom_passed = (result == "SUCCESS") and (confidence >= 0.7)

            if geom_passed and confidence >= 0.7:
                return (True, confidence, "CHALLENGE_PASSED")
            else:
                return (False, confidence, "GEOMETRIC_VALIDATION_FAILED")

        # 3. Client-verified mode fallback (without raw telemetry)
        if result == "SUCCESS" and confidence >= 0.7:
            return (True, confidence, "CHALLENGE_PASSED")

        if confidence < 0.7:
            return (False, confidence, "LOW_CONFIDENCE")

        return (False, confidence, "CHALLENGE_FAILED")
