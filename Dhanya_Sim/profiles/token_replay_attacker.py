"""Token replay attacker profile for Fair Drop adversarial simulation."""

import asyncio
from typing import Any, Dict, List, Optional

from .base_profile import BaseProfile


class TokenReplayAttacker(BaseProfile):
    """Simulates an attacker attempting token replay attacks.

    Behaviors:
    - Obtains one legitimate admission permit or entitlement token.
    - Replays the identical token 10-20 times across different requests or identities.
    - Tests permit expiration, nonce reuse rejection, and single-use entitlement constraints.
    - Expected backend invariant: replay_success_count == 0.
    """

    is_bot: bool = True
    profile_type: str = "token_replay_attacker"

    async def execute_registration_flow(
        self,
        campaign_id: str,
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        identity_id = identity.get("participant_id") or identity.get("account_id", "attacker_replay")
        replay_count = int(self.config.get("replay_count", 15))
        flow_summary: Dict[str, Any] = {
            "participant_id": identity_id,
            "permit_captured": False,
            "initial_reg_status": None,
            "replay_statuses": [],
        }

        # Step 1: Complete valid initial join to capture legitimate signed permit
        join_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/join",
            identity_id=identity_id,
            json_data={"participant_id": identity_id},
        )

        captured_permit: Optional[str] = None
        if join_resp and join_resp.status_code == 200:
            try:
                captured_permit = join_resp.json().get("admission_permit")
                flow_summary["permit_captured"] = bool(captured_permit)
            except Exception:
                pass

        # Step 2: Initial registration using the permit
        idempotency_key = self.generate_idempotency_key()
        first_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/register",
            identity_id=identity_id,
            idempotency_key=idempotency_key,
            json_data={
                "participant_id": identity_id,
                "campaign_id": campaign_id,
                "admission_permit": captured_permit,
                "idempotency_key": idempotency_key,
            },
        )
        flow_summary["initial_reg_status"] = first_resp.status_code if first_resp else None

        # Step 3: Replay the SAME permit across 10-20 different pseudo-identities
        for i in range(replay_count):
            replay_identity = f"{identity_id}_replay_{i}"
            new_key = self.generate_idempotency_key()
            rep_resp = await self.send_request(
                method="POST",
                path=f"/api/campaigns/{campaign_id}/register",
                identity_id=replay_identity,
                idempotency_key=new_key,
                json_data={
                    "participant_id": replay_identity,
                    "campaign_id": campaign_id,
                    "admission_permit": captured_permit,  # Replayed token
                    "idempotency_key": new_key,
                },
                retry_number=i + 1,
            )
            flow_summary["replay_statuses"].append(rep_resp.status_code if rep_resp else None)
            await asyncio.sleep(0.02)

        return flow_summary

    async def execute_claim_flow(
        self,
        entitlement_id: str,
    ) -> Dict[str, Any]:
        identity_id = self.config.get("identity_id", "attacker_replay")
        replay_count = int(self.config.get("replay_count", 10))
        claim_summary: Dict[str, Any] = {
            "entitlement_id": entitlement_id,
            "first_hold_status": None,
            "replay_hold_statuses": [],
        }

        # Step 1: Initial hold with legitimate entitlement
        first_hold = await self.send_request(
            method="POST",
            path=f"/api/entitlements/{entitlement_id}/hold",
            identity_id=identity_id,
            idempotency_key=self.generate_idempotency_key(),
            json_data={"entitlement_id": entitlement_id},
        )
        claim_summary["first_hold_status"] = first_hold.status_code if first_hold else None

        # Step 2: Replay the SAME entitlement across multiple concurrent hold requests
        for i in range(replay_count):
            rep_resp = await self.send_request(
                method="POST",
                path=f"/api/entitlements/{entitlement_id}/hold",
                identity_id=f"{identity_id}_clone_{i}",
                idempotency_key=self.generate_idempotency_key(),
                json_data={"entitlement_id": entitlement_id},
                retry_number=i + 1,
            )
            claim_summary["replay_hold_statuses"].append(rep_resp.status_code if rep_resp else None)

        return claim_summary
