"""Normal human profile.

Simulates a legitimate user following the standard registration flow:
  status check → join (get permit) → register → result

Includes realistic timing jitter (0.5–5 s between steps) to distinguish
this class from automated bots.
"""

from __future__ import annotations

import asyncio
import random

from simulator.profiles.base import BaseClient


class NormalHuman(BaseClient):
    """Legitimate participant with natural timing delays."""

    client_class = "normal_human"

    async def run(self) -> dict:
        # 1. Check campaign status
        await self.get_status()
        await asyncio.sleep(random.uniform(0.5, 2.0))

        # 2. Join to obtain an admission permit
        status, body = await self.join()
        await asyncio.sleep(random.uniform(0.5, 3.0))

        if status not in (200, 201):
            return {
                "client_class": self.client_class,
                "user_id": self.user["user_id"],
                "success": False,
                "stage": "join",
                "status": status,
            }

        # 3. Submit lottery registration
        reg_status, reg_body = await self.register()
        await asyncio.sleep(random.uniform(0.5, 5.0))

        # 4. Fetch result
        await self.get_result()

        return {
            "client_class": self.client_class,
            "user_id": self.user["user_id"],
            "success": reg_status in (200, 201),
            "register_status": reg_status,
        }
