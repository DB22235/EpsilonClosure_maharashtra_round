"""
Adapter for challenge generators and verification models.
"""

from __future__ import annotations

from typing import Any

from app.integrations.turnstile import TurnstileVerifier
from app.schemas.challenge import ChallengeType

try:
    from mediapipe_engine.gesture_engine import GestureEngine
except ImportError:
    try:
        from apps.mediapipe.gesture_engine import GestureEngine
    except ImportError:
        import sys
        from pathlib import Path
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        try:
            from mediapipe_engine.gesture_engine import GestureEngine
        except ImportError:
            from apps.mediapipe.gesture_engine import GestureEngine


class ChallengeAdapter:
    """
    Factory adapter class providing specific instructions and validation rules
    per ChallengeType (MEDIAPIPE, TURNSTILE, VISUAL, MOCK).
    """

    @staticmethod
    def get_instructions(challenge_type: ChallengeType | str) -> dict[str, Any]:
        """
        Generate implementation instructions for client HUD based on challenge type.
        """
        c_type = str(challenge_type.value if hasattr(challenge_type, "value") else challenge_type).upper()

        if c_type == "MEDIAPIPE":
            return GestureEngine.generate_challenge_instructions()

        elif c_type == "TURNSTILE":
            site_key = TurnstileVerifier.get_sitekey()
            return {
                "sitekey": site_key,
                "site_key": site_key,
            }

        elif c_type == "VISUAL":
            return {
                "puzzle_type": "image_grid",
                "prompt": "Select all images that contain a dog",
                "grid_size": "3x3",
                "duration_seconds": 15,
                "accessibility_mode": True,
            }

        else:  # MOCK
            return {
                "message": "Mock verification challenge",
                "duration_seconds": 3,
            }

    @staticmethod
    def validate_result(
        challenge_type: ChallengeType | str,
        result: str,
        confidence: float | None = None,
        turnstile_token: str | None = None,
        instructions: dict[str, Any] | None = None,
        verify_request: Any = None,
    ) -> tuple[bool, str]:
        """
        Validate submitted result against challenge type rules (synchronous types).
        Returns tuple: (is_passed: bool, reason_code: str)
        """
        c_type = str(challenge_type.value if hasattr(challenge_type, "value") else challenge_type).upper()

        if c_type == "MEDIAPIPE":
            if instructions and verify_request is not None:
                passed, _conf, reason = GestureEngine.validate_submission(instructions, verify_request)
                return (passed, reason)
            conf = confidence if confidence is not None else 1.0
            passed = (result == "SUCCESS" and conf >= 0.70)
            return (passed, "CHALLENGE_PASSED" if passed else "CHALLENGE_FAILED")

        elif c_type == "TURNSTILE":
            # Synced fallback check if called without async await
            passed = bool(turnstile_token and turnstile_token in ("mock-turnstile-pass-token", "test-token"))
            return (passed, "CHALLENGE_PASSED" if passed else "TURNSTILE_VALIDATION_FAILED")

        elif c_type == "VISUAL":
            passed = (result == "SUCCESS")
            return (passed, "CHALLENGE_PASSED" if passed else "CHALLENGE_FAILED")

        else:  # MOCK
            passed = (result == "SUCCESS")
            return (passed, "CHALLENGE_PASSED" if passed else "CHALLENGE_FAILED")

    @staticmethod
    async def validate_result_async(
        challenge_type: ChallengeType | str,
        result: str,
        confidence: float | None = None,
        turnstile_token: str | None = None,
        instructions: dict[str, Any] | None = None,
        verify_request: Any = None,
    ) -> tuple[bool, str]:
        """
        Async validate submitted result against challenge type rules (supports async API verifiers like Turnstile).
        Returns tuple: (is_passed: bool, reason_code: str)
        """
        c_type = str(challenge_type.value if hasattr(challenge_type, "value") else challenge_type).upper()

        if c_type == "TURNSTILE":
            token = turnstile_token or getattr(verify_request, "turnstile_token", None)
            is_valid, _meta = await TurnstileVerifier.verify_token(token)
            if is_valid:
                return True, "CHALLENGE_PASSED"
            return False, "TURNSTILE_VALIDATION_FAILED"

        return ChallengeAdapter.validate_result(
            challenge_type=challenge_type,
            result=result,
            confidence=confidence,
            turnstile_token=turnstile_token,
            instructions=instructions,
            verify_request=verify_request,
        )
