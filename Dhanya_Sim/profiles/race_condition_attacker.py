"""Race condition attacker profile for Fair Drop adversarial simulation."""

import asyncio
from typing import Any, Dict, List, Optional

from .base_profile import BaseProfile


class RaceConditionAttacker(BaseProfile):
    """Simulates concurrent race condition attacks against scarce inventory.

    Behaviors:
    - Sends 5-10 parallel hold requests for the EXACT SAME entitlement or seat.
    - Sends parallel redemption requests simultaneously.
    - Evaluates inventory correctness: exactly one request must transition the seat
      to HELD/CONFIRMED, and remaining parallel attempts must be rejected with 409/400.
    - Proves zero oversell and zero duplicate allocation under race conditions.
    """

    is_bot: bool = True
    profile_type: str = "race_condition_attacker"

    async def execute_registration_flow(
        self,
        campaign_id: str,
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        identity_id = identity.get("participant_id") or identity.get("account_id", "attacker_race")

        # Standard join to register normally first
        join_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/join",
            identity_id=identity_id,
            json_data={"participant_id": identity_id},
        )
        permit = join_resp.json().get("admission_permit") if (join_resp and join_resp.status_code == 200) else None

        idempotency_key = self.generate_idempotency_key()
        reg_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/register",
            identity_id=identity_id,
            idempotency_key=idempotency_key,
            json_data={
                "participant_id": identity_id,
                "campaign_id": campaign_id,
                "admission_permit": permit,
                "idempotency_key": idempotency_key,
            },
        )
        return {
            "participant_id": identity_id,
            "status": "ACCEPTED" if (reg_resp and reg_resp.status_code in (200, 201)) else "REJECTED",
        }

    async def execute_claim_flow(
        self,
        entitlement_id: str,
    ) -> Dict[str, Any]:
        concurrency = int(self.config.get("race_concurrency", 8))
        identity_id = self.config.get("identity_id", "attacker_race")

        # Step 1: Send parallel HOLD requests for the SAME entitlement_id
        async def concurrent_hold(worker_id: int) -> Optional[int]:
            key = self.generate_idempotency_key()
            resp = await self.send_request(
                method="POST",
                path=f"/api/entitlements/{entitlement_id}/hold",
                identity_id=f"{identity_id}_worker_{worker_id}",
                idempotency_key=key,
                json_data={"entitlement_id": entitlement_id},
            )
            return resp.status_code if resp else None

        hold_tasks = [concurrent_hold(i) for i in range(concurrency)]
        hold_results: List[Optional[int]] = await asyncio.gather(*hold_tasks, return_exceptions=False)

        hold_successes = sum(1 for code in hold_results if code in (200, 201))
        hold_conflicts = sum(1 for code in hold_results if code in (409, 400, 422, 403))

        # Step 2: Send parallel REDEEM requests simultaneously
        async def concurrent_redeem(worker_id: int) -> Optional[int]:
            key = self.generate_idempotency_key()
            resp = await self.send_request(
                method="POST",
                path=f"/api/entitlements/{entitlement_id}/redeem",
                identity_id=f"{identity_id}_worker_{worker_id}",
                idempotency_key=key,
                json_data={"entitlement_id": entitlement_id, "human_validation": True},
            )
            return resp.status_code if resp else None

        redeem_tasks = [concurrent_redeem(i) for i in range(concurrency)]
        redeem_results: List[Optional[int]] = await asyncio.gather(*redeem_tasks, return_exceptions=False)

        redeem_successes = sum(1 for code in redeem_results if code in (200, 201))
        redeem_conflicts = sum(1 for code in redeem_results if code in (409, 400, 422, 403))

        return {
            "entitlement_id": entitlement_id,
            "concurrency": concurrency,
            "hold_results": hold_results,
            "hold_successes": hold_successes,
            "hold_conflicts": hold_conflicts,
            "redeem_results": redeem_results,
            "redeem_successes": redeem_successes,
            "redeem_conflicts": redeem_conflicts,
            "inventory_invariant_passed": (hold_successes <= 1 and redeem_successes <= 1),
        }
