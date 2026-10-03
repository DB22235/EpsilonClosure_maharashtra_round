"""Race condition attacker profile.

After the lottery is drawn, a winning user fires 10 parallel seat-hold
requests for the same entitlement with DIFFERENT idempotency keys.

A correct backend must:
  - Confirm exactly one hold.
  - Reject all others with CONFLICT / ALREADY_HELD / SEAT_TAKEN.
  - Never allow two holds on the same seat simultaneously.

Usage: The scenario runner should obtain the user's result first and
pass entitlement_id in user['entitlement_id'] before constructing
this profile.  If no entitlement is present (user is not a winner)
the profile records the skip and returns early.
"""

from __future__ import annotations

import asyncio
import uuid

from profiles.base import BaseClient

RACE_PARALLEL = 10


class RaceAttacker(BaseClient):
    """Attacker that fires parallel hold requests for the same entitlement."""

    client_class = "race_attacker"

    async def run(self) -> dict:
        # Fetch result first to discover entitlement_id
        result_status, result_body = await self.get_result()
        entitlement_id = None
        if isinstance(result_body, dict):
            entitlement_id = result_body.get("entitlement_id")

        if not entitlement_id:
            return {
                "client_class": self.client_class,
                "user_id": self.user["user_id"],
                "success": False,
                "stage": "result",
                "reason": "no_entitlement",
            }

        # Fire RACE_PARALLEL hold requests with different idempotency keys
        async def _hold(i: int) -> tuple[int, dict]:
            key = f"race_{self.user['user_id']}_{entitlement_id}_{i}_{uuid.uuid4().hex[:6]}"
            return await self._request(
                "POST",
                f"/entitlements/{entitlement_id}/hold",
                operation="hold",
                json_body={},
                idempotency_key=key,
                extra={"race_slot": i},
            )

        results = await asyncio.gather(
            *[_hold(i) for i in range(RACE_PARALLEL)], return_exceptions=True
        )

        statuses = []
        for r in results:
            if isinstance(r, Exception):
                statuses.append(0)
            else:
                statuses.append(r[0])

        confirmed = [s for s in statuses if s in (200, 201)]
        conflicts = [s for s in statuses if s in (409, 423)]

        return {
            "client_class": self.client_class,
            "user_id": self.user["user_id"],
            "success": len(confirmed) == 1,
            "entitlement_id": entitlement_id,
            "parallel_holds": RACE_PARALLEL,
            "confirmed_holds": len(confirmed),
            "conflict_responses": len(conflicts),
            "no_oversell": len(confirmed) <= 1,
        }
