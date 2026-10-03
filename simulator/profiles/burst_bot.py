"""Burst bot profile.

Joins once to obtain a permit, then fires 10 parallel register calls
with the SAME idempotency key.  A correct backend must:
  - Accept the first request.
  - Return the same idempotent result for all subsequent identical keys.
  - Not create more than one registration for this user.

The burst simulates clients that hammer the same endpoint hoping
repeated volume converts to extra lottery entries.
"""

from __future__ import annotations

import asyncio

from profiles.base import BaseClient

BURST_SIZE = 10


class BurstBot(BaseClient):
    """Bot that fires many parallel register calls with the same idempotency key."""

    client_class = "burst_bot"

    async def run(self) -> dict:
        # 1. Obtain a permit (one join is sufficient)
        join_status, _ = await self.join()

        if join_status not in (200, 201):
            return {
                "client_class": self.client_class,
                "user_id": self.user["user_id"],
                "success": False,
                "stage": "join",
                "join_status": join_status,
            }

        # 2. Fire BURST_SIZE parallel register requests — SAME idempotency key
        idem_key = f"burst_{self.user['user_id']}_{self.campaign_id}"
        tasks = [
            self.register(idempotency_key=idem_key)
            for _ in range(BURST_SIZE)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        statuses = []
        for r in results:
            if isinstance(r, Exception):
                statuses.append(0)
            else:
                statuses.append(r[0])

        successful = [s for s in statuses if s in (200, 201)]
        return {
            "client_class": self.client_class,
            "user_id": self.user["user_id"],
            "success": len(successful) > 0,
            "burst_size": BURST_SIZE,
            "successful_responses": len(successful),
            "distinct_statuses": list(set(statuses)),
        }
