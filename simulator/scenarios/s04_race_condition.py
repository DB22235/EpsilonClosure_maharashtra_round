"""Scenario 04: Race Condition
Run lottery first, select winners, then RaceAttackers fire 10 concurrent /hold requests
on the same entitlement.
Expectation: Exactly 1 hold succeeds, 9 fail (409 Conflict / Locked).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import httpx

from simulator.config import settings
from simulator.fixtures.seed_users import load_users
from simulator.metrics.collector import collector
from simulator.profiles.normal_human import NormalHuman
from simulator.profiles.race_attacker import RaceAttacker
from simulator.scenarios.admin_helper import create_test_campaign, get_admin_token, run_lottery

logger = logging.getLogger(__name__)


async def run() -> Dict[str, Any]:
    """Execute Scenario 04."""
    collector.reset()
    users = load_users()
    if len(users) < 10:
        raise ValueError("Need at least 10 seeded users. Run seed_users.py first.")

    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=30.0) as client:
        admin_token = await get_admin_token(client)
        campaign = await create_test_campaign(
            admin_token=admin_token,
            capacity=5,
            title="S04 Race Condition: Entitlement Claim",
            client=client,
        )
        campaign_id = campaign.get("id") or campaign.get("campaign_id")
        logger.info(f"S04 started for campaign {campaign_id}")

        # Register 10 users cleanly first so we have lottery participants
        setup_clients = [
            NormalHuman(u["user_id"], u["token"], campaign_id, http_client=client)
            for u in users[:10]
        ]
        await asyncio.gather(*[c.run() for c in setup_clients], return_exceptions=True)

        # Run lottery to issue entitlements
        await run_lottery(admin_token, campaign_id, client)

        # Now convert winners into RaceAttackers
        race_attackers = [
            RaceAttacker(u["user_id"], u["token"], campaign_id, http_client=client)
            for u in users[:10]
        ]

        # Each attacker will attempt 10 parallel holds on whatever entitlement they won
        results = await asyncio.gather(*[a.run() for a in race_attackers], return_exceptions=True)

    return {
        "scenario": "s04_race_condition",
        "campaign_id": campaign_id,
        "total_attackers": len(race_attackers),
    }
