"""Retry bot profile.

Simulates a client that repeats the same register call 3 times with
the SAME idempotency key, mimicking a user that lost a network response
and retried.

A correct backend must return the same logical result for each retry —
not create extra registrations.  This tests idempotency under the
"retry on uncertain outcome" pattern.
"""

from __future__ import annotations

import asyncio

from simulator.profiles.base import BaseClient

RETRY_COUNT = 3
RETRY_DELAY_S = 0.1


class RetryBot(BaseClient):
    """Bot that retries register 3x with the same idempotency key."""

    client_class = "retry_bot"

    async def run(self) -> dict:
        # 1. Join to obtain a permit
        join_status, _ = await self.join()
        if join_status not in (200, 201):
            return {
                "client_class": self.client_class,
                "user_id": self.user["user_id"],
                "success": False,
                "stage": "join",
            }

        # 2. Register RETRY_COUNT times with the SAME idempotency key
        idem_key = f"retry_{self.user['user_id']}_{self.campaign_id}"
        statuses = []
        last_body: dict = {}

        for attempt in range(RETRY_COUNT):
            status, body = await self._request(
                "POST",
                f"/campaigns/{self.campaign_id}/register",
                operation="register",
                json_body={
                    "admission_token": (self.permit or {}).get("admission_token", ""),
                    "nonce": (self.permit or {}).get("nonce", ""),
                },
                idempotency_key=idem_key,
                retry_number=attempt,
            )
            statuses.append(status)
            last_body = body
            if attempt < RETRY_COUNT - 1:
                await asyncio.sleep(RETRY_DELAY_S)

        return {
            "client_class": self.client_class,
            "user_id": self.user["user_id"],
            "success": any(s in (200, 201) for s in statuses),
            "retry_statuses": statuses,
            "all_same": len(set(statuses)) == 1,
        }
