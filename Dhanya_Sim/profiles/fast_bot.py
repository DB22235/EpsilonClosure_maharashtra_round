"""Fast bot client profile for Fair Drop adversarial simulation."""

import asyncio
import random
from typing import Any, Dict, Optional

from .base_profile import BaseProfile


class FastBot(BaseProfile):
    """Simulates a low-latency, automated speed bot.

    Behaviors:
    - Minimal execution delays (0.05-0.2s).
    - Attempts to win solely through arrival speed.
    - Single identity, single attempt, no retries.
    - Bypasses non-essential browsing steps.
    """

    is_bot: bool = True
    profile_type: str = "fast_bot"

    async def execute_registration_flow(
        self,
        campaign_id: str,
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        identity_id = identity.get("participant_id") or identity.get("account_id", "bot_fast")
        flow_summary = {"participant_id": identity_id, "status": "PENDING"}

        # Immediate join with sub-second delay
        await asyncio.sleep(random.uniform(0.05, 0.2))
        join_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/join",
            identity_id=identity_id,
            json_data={"participant_id": identity_id, "email": identity.get("email")},
        )

        admission_permit: Optional[str] = None
        if join_resp and join_resp.status_code == 200:
            try:
                admission_permit = join_resp.json().get("admission_permit")
            except Exception:
                pass

        # Immediate registration with minimal delay
        await asyncio.sleep(random.uniform(0.05, 0.2))
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
                "idempotency_key": idempotency_key,
            },
        )

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
        identity_id = self.config.get("identity_id", "bot_fast")
        claim_summary = {"entitlement_id": entitlement_id, "status": "PENDING"}

        await asyncio.sleep(random.uniform(0.05, 0.1))
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

        await asyncio.sleep(random.uniform(0.05, 0.1))
        redeem_resp = await self.send_request(
            method="POST",
            path=f"/api/entitlements/{entitlement_id}/redeem",
            identity_id=identity_id,
            idempotency_key=self.generate_idempotency_key(),
            json_data={"entitlement_id": entitlement_id, "human_validation": True},
        )

        claim_summary["status"] = "CONFIRMED" if (redeem_resp and redeem_resp.status_code in (200, 201)) else "REDEEM_FAILED"
        return claim_summary
