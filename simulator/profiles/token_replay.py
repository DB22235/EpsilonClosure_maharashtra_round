"""Token replay attacker profile.

Joins once to obtain a valid admission permit, then attempts to use
the SAME permit 5 times with DIFFERENT idempotency keys.

A correct backend must:
  - Accept the first use of the permit.
  - Reject subsequent uses with error code PERMIT_EXPIRED or PERMIT_USED.

This tests single-use / short-lived admit token enforcement.
"""

from __future__ import annotations

import asyncio
import uuid

from simulator.profiles.base import BaseClient

REPLAY_COUNT = 5
REPLAY_DELAY_S = 0.05


class TokenReplayAttacker(BaseClient):
    """Attacker that reuses the same admission permit multiple times."""

    client_class = "token_replay"

    async def run(self) -> dict:
        # 1. Obtain a fresh permit
        join_status, join_body = await self.join()
        if join_status not in (200, 201) or not self.permit:
            return {
                "client_class": self.client_class,
                "user_id": self.user["user_id"],
                "success": False,
                "stage": "join",
            }

        # 2. Snapshot the permit before the first use potentially invalidates it
        stale_permit = dict(self.permit)

        statuses: list[int] = []
        error_codes: list[str | None] = []

        for i in range(REPLAY_COUNT):
            # Always supply a FRESH idempotency key so each attempt is logically new
            fresh_key = f"replay_{self.user['user_id']}_{self.campaign_id}_{uuid.uuid4().hex[:8]}"
            status, body = await self._request(
                "POST",
                f"/campaigns/{self.campaign_id}/register",
                operation="register",
                json_body={
                    "admission_token": stale_permit.get("admission_token", ""),
                    "nonce": stale_permit.get("nonce", ""),
                },
                idempotency_key=fresh_key,
                retry_number=i,
                extra={"replay_attempt": i},
            )
            statuses.append(status)
            error_codes.append(
                body.get("error", {}).get("code") if isinstance(body, dict) else None
            )
            await asyncio.sleep(REPLAY_DELAY_S)

        successes = [s for s in statuses if s in (200, 201)]
        rejections = [s for s in statuses if s in (400, 401, 403, 409, 410, 422)]

        return {
            "client_class": self.client_class,
            "user_id": self.user["user_id"],
            "success": len(successes) > 0,
            "replay_count": REPLAY_COUNT,
            "statuses": statuses,
            "error_codes": error_codes,
            "replays_rejected": len(rejections),
            "replay_protection_active": len(rejections) >= REPLAY_COUNT - 1,
        }
