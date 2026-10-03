"""Retry bot client profile for Fair Drop adversarial simulation."""

import asyncio
from typing import Any, Dict, List, Optional

from .base_profile import BaseProfile


class RetryBot(BaseProfile):
    """Simulates an aggressive client retrying requests on short timeouts.

    Behaviors:
    - Sends requests and rapidly retries after short delay (0.5s).
    - Preserves identical idempotency key on retry attempts to verify backend idempotency.
    - Configurable retry count (default 5).
    - Tests invariant: different payload with same idempotency key must be rejected (409/conflict).
    """

    is_bot: bool = True
    profile_type: str = "retry_bot"

    async def execute_registration_flow(
        self,
        campaign_id: str,
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        identity_id = identity.get("participant_id") or identity.get("account_id", "bot_retry")
        max_retries = int(self.config.get("retry_count", 5))
        idempotency_key = self.generate_idempotency_key()

        flow_summary: Dict[str, Any] = {
            "participant_id": identity_id,
            "idempotency_key": idempotency_key,
            "attempts": [],
            "conflict_test_status": None,
        }

        # Step 1: Initial join
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

        # Step 2: Identical retries with SAME idempotency key and same payload
        base_payload = {
            "participant_id": identity_id,
            "campaign_id": campaign_id,
            "admission_permit": admission_permit,
            "idempotency_key": idempotency_key,
            "payload_version": 1,
        }

        for attempt in range(max_retries):
            resp = await self.send_request(
                method="POST",
                path=f"/api/campaigns/{campaign_id}/register",
                identity_id=identity_id,
                idempotency_key=idempotency_key,
                json_data=base_payload,
                retry_number=attempt,
                timeout=0.5,
            )
            flow_summary["attempts"].append({
                "attempt": attempt,
                "status_code": resp.status_code if resp else None,
            })
            await asyncio.sleep(0.5)

        # Step 3: Conflict invariant test — DIFFERENT payload with SAME idempotency key
        altered_payload = {
            "participant_id": f"{identity_id}_altered",
            "campaign_id": campaign_id,
            "admission_permit": admission_permit,
            "idempotency_key": idempotency_key,
            "payload_version": 2,
        }
        conflict_resp = await self.send_request(
            method="POST",
            path=f"/api/campaigns/{campaign_id}/register",
            identity_id=identity_id,
            idempotency_key=idempotency_key,
            json_data=altered_payload,
            retry_number=max_retries,
        )
        flow_summary["conflict_test_status"] = (
            conflict_resp.status_code if conflict_resp else None
        )

        return flow_summary

    async def execute_claim_flow(
        self,
        entitlement_id: str,
    ) -> Dict[str, Any]:
        identity_id = self.config.get("identity_id", "bot_retry")
        idempotency_key = self.generate_idempotency_key()
        max_retries = int(self.config.get("retry_count", 3))
        hold_statuses: List[Optional[int]] = []

        # Retry hold with same key
        for attempt in range(max_retries):
            resp = await self.send_request(
                method="POST",
                path=f"/api/entitlements/{entitlement_id}/hold",
                identity_id=identity_id,
                idempotency_key=idempotency_key,
                json_data={"entitlement_id": entitlement_id},
                retry_number=attempt,
                timeout=0.5,
            )
            hold_statuses.append(resp.status_code if resp else None)
            await asyncio.sleep(0.5)

        return {
            "entitlement_id": entitlement_id,
            "hold_statuses": hold_statuses,
        }
