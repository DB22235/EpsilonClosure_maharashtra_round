"""Burst bot client profile for Fair Drop adversarial simulation."""

import asyncio
from typing import Any, Dict, List, Optional

from .base_profile import BaseProfile


class BurstBot(BaseProfile):
    """Simulates a high-concurrency burst flood attacker.

    Behaviors:
    - Sends 20-100 concurrent requests in parallel using asyncio.gather.
    - First wave sends identical idempotency keys (stress-testing deduplication).
    - Second wave varies idempotency keys (stress-testing rate limits and queue capacity).
    - Tests atomic constraints and deduplication efficiency under concurrency.
    """

    is_bot: bool = True
    profile_type: str = "burst_bot"

    async def execute_registration_flow(
        self,
        campaign_id: str,
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        identity_id = identity.get("participant_id") or identity.get("account_id", "bot_burst")
        burst_size = int(self.config.get("burst_size", 25))
        flow_summary: Dict[str, Any] = {
            "participant_id": identity_id,
            "burst_size": burst_size,
            "wave1_identical_key_results": [],
            "wave2_varied_key_results": [],
        }

        # Step 1: Initial join to acquire permit
        join_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/join",
            identity_id=identity_id,
            json_data={"participant_id": identity_id},
        )
        admission_permit: Optional[str] = None
        if join_resp and join_resp.status_code == 200:
            try:
                admission_permit = join_resp.json().get("admission_permit")
            except Exception:
                pass

        # Wave 1: Parallel burst with SAME idempotency key (dedup test)
        shared_key = self.generate_idempotency_key()

        async def send_wave1() -> Optional[int]:
            resp = await self.send_request(
                method="POST",
                path=f"/api/campaigns/{campaign_id}/register",
                identity_id=identity_id,
                idempotency_key=shared_key,
                json_data={
                    "participant_id": identity_id,
                    "campaign_id": campaign_id,
                    "admission_permit": admission_permit,
                    "idempotency_key": shared_key,
                },
            )
            return resp.status_code if resp else None

        wave1_tasks = [send_wave1() for _ in range(burst_size)]
        wave1_outcomes = await asyncio.gather(*wave1_tasks, return_exceptions=True)
        flow_summary["wave1_identical_key_results"] = [
            code for code in wave1_outcomes if isinstance(code, int)
        ]

        # Wave 2: Parallel burst with VARIED idempotency keys (rate-limit test)
        async def send_wave2() -> Optional[int]:
            key = self.generate_idempotency_key()
            resp = await self.send_request(
                method="POST",
                path=f"/api/campaigns/{campaign_id}/register",
                identity_id=identity_id,
                idempotency_key=key,
                json_data={
                    "participant_id": identity_id,
                    "campaign_id": campaign_id,
                    "admission_permit": admission_permit,
                    "idempotency_key": key,
                },
            )
            return resp.status_code if resp else None

        wave2_tasks = [send_wave2() for _ in range(burst_size)]
        wave2_outcomes = await asyncio.gather(*wave2_tasks, return_exceptions=True)
        flow_summary["wave2_varied_key_results"] = [
            code for code in wave2_outcomes if isinstance(code, int)
        ]

        return flow_summary

    async def execute_claim_flow(
        self,
        entitlement_id: str,
    ) -> Dict[str, Any]:
        identity_id = self.config.get("identity_id", "bot_burst")
        burst_size = min(int(self.config.get("burst_size", 10)), 15)

        # Burst hold requests
        async def send_hold() -> Optional[int]:
            resp = await self.send_request(
                method="POST",
                path=f"/api/entitlements/{entitlement_id}/hold",
                identity_id=identity_id,
                idempotency_key=self.generate_idempotency_key(),
                json_data={"entitlement_id": entitlement_id},
            )
            return resp.status_code if resp else None

        hold_tasks = [send_hold() for _ in range(burst_size)]
        hold_results = await asyncio.gather(*hold_tasks, return_exceptions=True)
        return {
            "entitlement_id": entitlement_id,
            "hold_results": [c for c in hold_results if isinstance(c, int)],
        }
