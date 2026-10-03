"""Fast bot profile.

Attempts to win by registering immediately (skipping join first),
then performs the correct flow if the first attempt is rejected.

This tests that the backend enforces permit requirements before
the frontend enforces them — speed-only bots should not succeed.
"""

from __future__ import annotations

import asyncio
import random

from simulator.profiles.base import BaseClient


class FastBot(BaseClient):
    """Bot that skips join and immediately calls register."""

    client_class = "fast_bot"

    async def run(self) -> dict:
        # 1. Skip join — attempt register without a valid permit (expect rejection)
        status1, body1 = await self.register(
            idempotency_key=f"fast_skip_{self.user['user_id']}_{self.campaign_id}"
        )
        await asyncio.sleep(random.uniform(0.05, 0.2))

        # 2. If rejected, do the correct flow (join then register)
        if status1 not in (200, 201):
            join_status, _ = await self.join()
            await asyncio.sleep(random.uniform(0.05, 0.15))
            if join_status in (200, 201):
                status2, body2 = await self.register()
                return {
                    "client_class": self.client_class,
                    "user_id": self.user["user_id"],
                    "success": status2 in (200, 201),
                    "skip_rejected": True,
                    "register_status": status2,
                }

        return {
            "client_class": self.client_class,
            "user_id": self.user["user_id"],
            "success": status1 in (200, 201),
            "skip_rejected": False,
            "register_status": status1,
        }
