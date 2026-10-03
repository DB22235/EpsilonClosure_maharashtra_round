"""Scenario 03: Replay Attack
Attacker obtains permit, attempts to register 5 times with DIFFERENT Idempotency-Keys.
Expectation: First registration 200/201, subsequent 4 rejected (409 Conflict / Permit consumed).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import httpx

from simulator.config import settings
from simulator.fixtures.seed_users import load_users
from simulator.metrics.collector import collector
from simulator.profiles.token_replay import TokenReplayAttacker
from simulator.scenarios.admin_helper import create_test_campaign, get_admin_token

logger = logging.getLogger(__name__)


async def run() -> Dict[str, Any]:
    """Execute Scenario 03."""
    collector.reset()
    users = load_users()
    if not users:
        raise ValueError("Need at least 1 seeded user. Run seed_users.py first.")

    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=30.0) as client:
        admin_token = await get_admin_token(client)
        campaign = await create_test_campaign(
            admin_token=admin_token,
            capacity=10,
            title="S03 Replay Attack",
            client=client,
        )
        campaign_id = campaign.get("id") or campaign.get("campaign_id")
        logger.info(f"S03 started for campaign {campaign_id}")

        # Use 10 TokenReplayAttackers concurrently
        attackers = [
            TokenReplayAttacker(
                user_id=u["user_id"],
                token=u["token"],
                campaign_id=campaign_id,
                http_client=client,
            )
            for u in users[:10]
        ]

        tasks = [a.run() for a in attackers]
        await asyncio.gather(*tasks, return_exceptions=True)

    return {
        "scenario": "s03_replay_attack",
        "campaign_id": campaign_id,
        "total_clients": len(attackers),
    }
