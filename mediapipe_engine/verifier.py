"""
GestureVerifier module for MediaPipe real-time challenge verification.
"""

from __future__ import annotations
from typing import Any

from .detectors import is_thumbs_up, is_valid_swipe, is_valid_move


class GestureVerifier:
    """
    Real-time gesture verifier tracking static poses and dynamic trajectories.
    """

    def __init__(self, target_gesture: str = "OPEN", required_hand: str = "LEFT") -> None:
        self.target_gesture = target_gesture.upper()
        self.required_hand = required_hand.upper()
        self.point_history: list[list[float]] = []

    def set_remote_target(self, gesture: str, hand: str) -> None:
        self.target_gesture = gesture.upper()
        self.required_hand = hand.upper()
        self.point_history.clear()

    def process_frame(
        self,
        detected_gesture: str,
        confidence: float,
        hand_label: str,
        landmarks: list[list[float]] | None = None,
    ) -> dict[str, Any]:
        """
        Process single frame detection result.
        """
        hand_match = hand_label.upper() == self.required_hand
        if not hand_match:
            return {
                "verified": False,
                "reason": "HAND_MISMATCH",
                "confidence": confidence,
                "hand_used": hand_label,
            }

        if landmarks and len(landmarks) >= 21:
            wrist = landmarks[0]
            self.point_history.append([float(wrist[0]), float(wrist[1])])

        # Validate based on target
        if self.target_gesture == "THUMBS_UP":
            valid = is_thumbs_up(landmarks or [])
        elif self.target_gesture == "SWIPE":
            valid = is_valid_swipe(self.point_history)
        elif self.target_gesture == "MOVE":
            valid = is_valid_move(self.point_history)
        else:
            valid = detected_gesture.upper() == self.target_gesture and confidence >= 0.7

        return {
            "verified": valid,
            "reason": "CHALLENGE_PASSED" if valid else "GEOMETRIC_VALIDATION_FAILED",
            "confidence": confidence,
            "hand_used": hand_label,
        }
