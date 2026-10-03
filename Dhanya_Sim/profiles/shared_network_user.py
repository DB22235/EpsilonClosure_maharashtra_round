"""Shared network user profile for Fair Drop adversarial simulation."""

import asyncio
import random
from typing import Any, Dict, List, Optional

from .base_profile import BaseProfile


class SharedNetworkUser(BaseProfile):
    """Simulates legitimate human participants sharing a common egress IP.

    Scenario: Corporate NAT, university campus, or public WiFi where hundreds of
    distinct humans legitimately share a single public IP address.

    Behaviors:
    - Multiple distinct, verified participant identities (10-20).
    - All requests include the identical simulated IP header (`X-Forwarded-For`).
    - Standard human pacing and interaction delays.
    - Verifies that IP-only rate limiting does not falsely reject legitimate participants.
    """

    profile_type: str = "shared_network_user"

    async def execute_registration_flow(
        self,
        campaign_id: str,
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        num_users = int(self.config.get("shared_users_count", 15))
        shared_ip = identity.get("shared_ip", "198.51.100.42")
        headers = {"X-Forwarded-For": shared_ip}
        results: List[Dict[str, Any]] = []

        for i in range(num_users):
            user_id = f"shared_nat_user_{i:02d}"
            # Human pacing
            await asyncio.sleep(random.uniform(0.5, 2.0))

            # Step 1: Join
            join_resp = await self.send_request(
                method="POST",
                path=f"/api/campaigns/{campaign_id}/join",
                identity_id=user_id,
                headers=headers,
                json_data={"participant_id": user_id, "email": f"{user_id}@campus.edu"},
            )

            permit: Optional[str] = None
            if join_resp and join_resp.status_code == 200:
                try:
                    permit = join_resp.json().get("admission_permit")
                except Exception:
                    pass

            # Step 2: Register
            idempotency_key = self.generate_idempotency_key()
            reg_resp = await self.send_request(
                method="POST",
                path=f"/api/campaigns/{campaign_id}/register",
                identity_id=user_id,
                idempotency_key=idempotency_key,
                headers=headers,
                json_data={
                    "participant_id": user_id,
                    "campaign_id": campaign_id,
                    "admission_permit": permit,
                    "idempotency_key": idempotency_key,
                },
            )

            results.append({
                "participant_id": user_id,
                "status_code": reg_resp.status_code if reg_resp else None,
                "accepted": (reg_resp is not None and reg_resp.status_code in (200, 201)),
            })

        successful_registrations = sum(1 for r in results if r["accepted"])
        false_positive_blocks = sum(1 for r in results if r["status_code"] == 429)

        return {
            "shared_ip": shared_ip,
            "total_users": num_users,
            "successful_registrations": successful_registrations,
            "false_positive_blocks": false_positive_blocks,
            "results": results,
        }

    async def execute_claim_flow(
        self,
        entitlement_id: str,
    ) -> Dict[str, Any]:
        identity_id = self.config.get("identity_id", "shared_claimant")
        shared_ip = self.config.get("shared_ip", "198.51.100.42")
        headers = {"X-Forwarded-For": shared_ip}

        await asyncio.sleep(random.uniform(0.5, 1.5))
        hold_resp = await self.send_request(
            method="POST",
            path=f"/api/entitlements/{entitlement_id}/hold",
            identity_id=identity_id,
            headers=headers,
            idempotency_key=self.generate_idempotency_key(),
            json_data={"entitlement_id": entitlement_id},
        )
        return {
            "entitlement_id": entitlement_id,
            "status": "HOLD_ACCEPTED" if (hold_resp and hold_resp.status_code in (200, 201)) else "HOLD_FAILED",
        }
