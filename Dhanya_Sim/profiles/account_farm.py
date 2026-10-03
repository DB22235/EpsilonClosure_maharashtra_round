"""Account farm client profile for Fair Drop adversarial simulation."""

import asyncio
from typing import Any, Dict, List, Optional

from .base_profile import BaseProfile


class AccountFarm(BaseProfile):
    """Simulates a multi-account bot farm attacker.

    Behaviors:
    - Generates N distinct identities (configurable, default 50).
    - Each identity registers once to test one-entry-per-participant limits.
    - Intentionally shares clustered email domain aliases (`farm_user+N@syndicate.io`)
      and common phone prefixes (`+15550100xxx`) to trigger duplicate identity
      relationship checks and risk scoring.
    """

    is_bot: bool = True
    profile_type: str = "account_farm"

    async def execute_registration_flow(
        self,
        campaign_id: str,
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        farm_size = int(self.config.get("farm_size", 50))
        cluster_id = identity.get("cluster_id", "syndicate_01")
        results: List[Dict[str, Any]] = []

        for i in range(farm_size):
            farm_identity_id = f"farm_{cluster_id}_{i:03d}"
            # Clustered alias and phone pattern to test relationship risk checks
            farm_email = f"operator+{cluster_id}_{i}@syndicate.io"
            farm_phone = f"+1555010{i:04d}"

            # Join
            join_resp = await self.send_request(
                method="POST",
                path=f"/api/campaigns/{campaign_id}/join",
                identity_id=farm_identity_id,
                json_data={
                    "participant_id": farm_identity_id,
                    "email": farm_email,
                    "phone": farm_phone,
                },
            )

            permit: Optional[str] = None
            if join_resp and join_resp.status_code == 200:
                try:
                    permit = join_resp.json().get("admission_permit")
                except Exception:
                    pass

            # Register
            idempotency_key = self.generate_idempotency_key()
            reg_resp = await self.send_request(
                method="POST",
                path=f"/api/campaigns/{campaign_id}/register",
                identity_id=farm_identity_id,
                idempotency_key=idempotency_key,
                json_data={
                    "participant_id": farm_identity_id,
                    "campaign_id": campaign_id,
                    "admission_permit": permit,
                    "idempotency_key": idempotency_key,
                    "email": farm_email,
                    "phone": farm_phone,
                },
            )

            results.append({
                "identity_id": farm_identity_id,
                "status_code": reg_resp.status_code if reg_resp else None,
            })

            # Small delay between farm members
            await asyncio.sleep(float(self.config.get("interval", 0.05)))

        return {
            "farm_size": farm_size,
            "cluster_id": cluster_id,
            "registrations": results,
        }

    async def execute_claim_flow(
        self,
        entitlement_id: str,
    ) -> Dict[str, Any]:
        identity_id = self.config.get("identity_id", "farm_claimant")
        hold_resp = await self.send_request(
            method="POST",
            path=f"/api/entitlements/{entitlement_id}/hold",
            identity_id=identity_id,
            idempotency_key=self.generate_idempotency_key(),
            json_data={"entitlement_id": entitlement_id},
        )
        return {
            "entitlement_id": entitlement_id,
            "status": "HOLD_SUBMITTED" if (hold_resp and hold_resp.status_code in (200, 201)) else "HOLD_FAILED",
        }
