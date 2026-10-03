"""Normal human client profile for Fair Drop adversarial simulation."""

import asyncio
import random
from typing import Any, Dict, Optional

from .base_profile import BaseProfile


class NormalHuman(BaseProfile):
    """Simulates a legitimate human participant.

    Behaviors:
    - Single account, low request rate.
    - Sequential flow: join waiting room, check status, complete challenge if required, register.
    - Realistic inter-step delays (1-5s).
    - Simulated browser refresh (GET status) and occasional reconnect.
    - Slower human challenge completion (3-8s).
    """

    profile_type: str = "normal_human"

    async def execute_registration_flow(
        self,
        campaign_id: str,
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        identity_id = identity.get("participant_id") or identity.get("account_id", "user_human")
        flow_summary = {"participant_id": identity_id, "status": "PENDING", "steps": []}

        # Step 1: Join campaign waiting room
        await self.sim_delay(1.0, 5.0)
        join_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/join",
            identity_id=identity_id,
            json_data={"participant_id": identity_id, "email": identity.get("email")},
        )
        flow_summary["steps"].append("join")

        admission_permit: Optional[str] = None
        if join_resp and join_resp.status_code == 200:
            try:
                admission_permit = join_resp.json().get("admission_permit")
            except Exception:
                pass

        # Step 2: Simulated browser refresh / status check (50% chance)
        if random.random() < 0.5:
            await self.sim_delay(1.0, 3.0)
            await self.send_request(
                method="GET",
                path=f"/api/campaigns/{campaign_id}/status",
                identity_id=identity_id,
            )
            flow_summary["steps"].append("refresh_status")

        # Step 3: Simulated human challenge if requested or step-up required
        challenge_token: Optional[str] = None
        if join_resp and join_resp.status_code == 200 and join_resp.json().get("challenge_required"):
            await self.sim_delay(3.0, 8.0)  # Human reaction/challenge completion
            verify_resp = await self.send_request(
                method="POST",
                path="/api/challenges/verify",
                identity_id=identity_id,
                json_data={
                    "session_id": identity_id,
                    "campaign_id": campaign_id,
                    "challenge_type": "gesture",
                    "answer": "simulated_human_answer",
                },
            )
            flow_summary["steps"].append("challenge")
            if verify_resp and verify_resp.status_code == 200:
                challenge_token = verify_resp.json().get("verification_token")

        # Step 4: Register with unique idempotency key
        await self.sim_delay(1.0, 5.0)
        idempotency_key = self.generate_idempotency_key()
        reg_payload = {
            "participant_id": identity_id,
            "campaign_id": campaign_id,
            "admission_permit": admission_permit,
            "challenge_token": challenge_token,
            "idempotency_key": idempotency_key,
        }
        reg_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/register",
            identity_id=identity_id,
            idempotency_key=idempotency_key,
            json_data=reg_payload,
        )
        flow_summary["steps"].append("register")

        if reg_resp and reg_resp.status_code in (200, 201):
            flow_summary["status"] = "ACCEPTED"
            flow_summary["receipt"] = reg_resp.json()
        else:
            flow_summary["status"] = "REJECTED"

        return flow_summary

    async def execute_claim_flow(
        self,
        entitlement_id: str,
    ) -> Dict[str, Any]:
        identity_id = self.config.get("identity_id", "user_human")
        claim_summary = {"entitlement_id": entitlement_id, "status": "PENDING"}

        # Step 1: Hold seat
        await self.sim_delay(1.0, 3.0)
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

        # Step 2: Human review and validation delay
        await self.sim_delay(2.0, 5.0)

        # Step 3: Redeem seat
        redeem_resp = await self.send_request(
            method="POST",
            path=f"/api/entitlements/{entitlement_id}/redeem",
            identity_id=identity_id,
            idempotency_key=self.generate_idempotency_key(),
            json_data={"entitlement_id": entitlement_id, "human_validation": True},
        )

        if redeem_resp and redeem_resp.status_code in (200, 201):
            claim_summary["status"] = "CONFIRMED"
        else:
            claim_summary["status"] = "REDEEM_FAILED"

        return claim_summary
