"""Direct API bot profile.

Skips the join step entirely and calls register without any admission
permit.  Tests that the backend — not the frontend — enforces the
admission requirement.

Expected backend response: 401 (Unauthorized) or 422 (Unprocessable)
with error code ADMISSION_REQUIRED or INVALID_PERMIT.
"""

from __future__ import annotations

from profiles.base import BaseClient


class DirectAPIBot(BaseClient):
    """Bot that attempts register without a permit (no join step)."""

    client_class = "direct_api_bot"

    async def run(self) -> dict:
        # Call register with an empty / missing permit
        status, body = await self._request(
            "POST",
            f"/campaigns/{self.campaign_id}/register",
            operation="register",
            json_body={"admission_token": "", "nonce": ""},
            idempotency_key=f"direct_{self.user['user_id']}_{self.campaign_id}",
        )

        error_code = (
            body.get("error", {}).get("code")
            if isinstance(body, dict)
            else None
        )

        return {
            "client_class": self.client_class,
            "user_id": self.user["user_id"],
            "success": status in (200, 201),
            "status": status,
            "error_code": error_code,
            "backend_enforced": status in (400, 401, 403, 422),
        }
