"""Slow accessibility user profile for Fair Drop adversarial simulation."""

import asyncio
import random
from typing import Any, Dict, Optional

from .base_profile import BaseProfile


class SlowAccessibilityUser(BaseProfile):
    """Simulates a participant using assistive technology or experiencing high latency.

    Scenario: Users relying on screen readers, switch access, keyboard navigation,
    or experiencing slow internet connections.

    Behaviors:
    - High inter-step latency (5-15s delays).
    - Keyboard-only navigation metadata (no pointer/mouse telemetry).
    - Automatically requests accessible fallback if a challenge is triggered.
    - Evaluates system fairness: must NOT be penalized or quarantined solely
      due to slow completion times or alternative challenge pathways.
    """

    profile_type: str = "slow_accessibility_user"

    async def execute_registration_flow(
        self,
        campaign_id: str,
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        identity_id = identity.get("participant_id") or identity.get("account_id", "user_a11y")
        flow_summary: Dict[str, Any] = {
            "participant_id": identity_id,
            "flow_type": "keyboard_accessible",
            "status": "PENDING",
            "fallback_requested": False,
        }

        # Step 1: Slow deliberate join with assistive technology delay (collapsed in mock mode)
        await self.sim_delay(5.0, 10.0)
        join_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/join",
            identity_id=identity_id,
            json_data={
                "participant_id": identity_id,
                "client_metadata": {
                    "input_mode": "keyboard_only",
                    "screen_reader_detected": True,
                    "pointer_events": 0,
                },
            },
        )

        admission_permit: Optional[str] = None
        if join_resp and join_resp.status_code == 200:
            try:
                admission_permit = join_resp.json().get("admission_permit")
            except Exception:
                pass

        # Step 2: Extended deliberate pause (screen reading / navigating, collapsed in mock mode)
        await self.sim_delay(5.0, 12.0)

        # Step 3: Challenge fallback step if challenge is required
        challenge_token: Optional[str] = None
        if join_resp and join_resp.status_code == 200 and join_resp.json().get("challenge_required"):
            flow_summary["fallback_requested"] = True
            # Request audio/accessible fallback challenge
            fallback_resp = await self.send_request(
                method="POST",
                path="/api/challenges/fallback",
                identity_id=identity_id,
                json_data={
                    "session_id": identity_id,
                    "campaign_id": campaign_id,
                    "requested_fallback": "audio_or_accessible_captcha",
                },
            )
            # Patiently complete accessible challenge (collapsed in mock mode)
            await self.sim_delay(8.0, 15.0)
            verify_resp = await self.send_request(
                method="POST",
                path="/api/challenges/verify",
                identity_id=identity_id,
                json_data={
                    "session_id": identity_id,
                    "campaign_id": campaign_id,
                    "challenge_type": "accessible_fallback",
                    "answer": "simulated_accessible_verification",
                },
            )
            if verify_resp and verify_resp.status_code == 200:
                challenge_token = verify_resp.json().get("verification_token")

        # Step 4: Final registration with keyboard metadata (collapsed in mock mode)
        await self.sim_delay(5.0, 10.0)
        idempotency_key = self.generate_idempotency_key()
        reg_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/register",
            identity_id=identity_id,
            idempotency_key=idempotency_key,
            json_data={
                "participant_id": identity_id,
                "campaign_id": campaign_id,
                "admission_permit": admission_permit,
                "challenge_token": challenge_token,
                "idempotency_key": idempotency_key,
                "client_metadata": {
                    "input_mode": "keyboard_only",
                    "nav_latency_seconds": 25.0,
                },
            },
        )

        if reg_resp and reg_resp.status_code in (200, 201):
            flow_summary["status"] = "ACCEPTED"
            flow_summary["receipt"] = reg_resp.json()
        elif reg_resp and reg_resp.status_code == 429:
            flow_summary["status"] = "FALSE_POSITIVE_RATE_LIMITED"
        else:
            flow_summary["status"] = "REJECTED"

        return flow_summary

    async def execute_claim_flow(
        self,
        entitlement_id: str,
    ) -> Dict[str, Any]:
        identity_id = self.config.get("identity_id", "user_a11y")
        claim_summary = {"entitlement_id": entitlement_id, "status": "PENDING"}

        await self.sim_delay(5.0, 10.0)
        hold_resp = await self.send_request(
            method="POST",
            path=f"/api/entitlements/{entitlement_id}/hold",
            identity_id=identity_id,
            idempotency_key=self.generate_idempotency_key(),
            json_data={"entitlement_id": entitlement_id},
        )

        if not hold_resp or hold_resp.status_code not in (200, 201):
            claim_summary["status"] = "HOLD_FAILED"
            return claim_summary

        await self.sim_delay(5.0, 12.0)
        redeem_resp = await self.send_request(
            method="POST",
            path=f"/api/entitlements/{entitlement_id}/redeem",
            identity_id=identity_id,
            idempotency_key=self.generate_idempotency_key(),
            json_data={"entitlement_id": entitlement_id, "human_validation": True},
        )

        claim_summary["status"] = "CONFIRMED" if (redeem_resp and redeem_resp.status_code in (200, 201)) else "REDEEM_FAILED"
        return claim_summary
