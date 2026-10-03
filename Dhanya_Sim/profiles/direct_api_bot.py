"""Direct API bot client profile for Fair Drop adversarial simulation."""

from typing import Any, Dict

from .base_profile import BaseProfile


class DirectAPIBot(BaseProfile):
    """Simulates an attacker bypassing the frontend UI entirely.

    Behaviors:
    - Skips waiting room and admission permits completely.
    - Calls POST /api/campaigns/{id}/register directly with missing or bogus permits.
    - Calls POST /api/entitlements/{id}/hold directly with forged or empty entitlement IDs.
    - Tests that backend authority and validation enforce security, not client-side UI gating.
    """

    is_bot: bool = True
    profile_type: str = "direct_api_bot"

    async def execute_registration_flow(
        self,
        campaign_id: str,
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        identity_id = identity.get("participant_id") or identity.get("account_id", "bot_direct_api")
        idempotency_key = self.generate_idempotency_key()

        # Direct call to registration without join/permit
        reg_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/register",
            identity_id=identity_id,
            idempotency_key=idempotency_key,
            json_data={
                "participant_id": identity_id,
                "campaign_id": campaign_id,
                "admission_permit": None,  # Intentionally omitted/missing
                "idempotency_key": idempotency_key,
            },
        )

        return {
            "participant_id": identity_id,
            "bypassed_waiting_room": True,
            "status_code": reg_resp.status_code if reg_resp else None,
            "rejected_as_expected": (reg_resp is not None and reg_resp.status_code in (401, 403, 400)),
        }

    async def execute_claim_flow(
        self,
        entitlement_id: str,
    ) -> Dict[str, Any]:
        identity_id = self.config.get("identity_id", "bot_direct_api")

        # Direct call to hold with forged entitlement
        hold_resp = await self.send_request(
            method="POST",
            path="/api/entitlements/forged_unauthorized_token/hold",
            identity_id=identity_id,
            idempotency_key=self.generate_idempotency_key(),
            json_data={"entitlement_id": "forged_unauthorized_token"},
        )

        return {
            "attempted_forgery": True,
            "status_code": hold_resp.status_code if hold_resp else None,
            "rejected_as_expected": (hold_resp is not None and hold_resp.status_code in (401, 403, 404)),
        }
