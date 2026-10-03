"""Scenario 01: Baseline
50 NormalHuman users, 50 capacity, staggered entry.
Tests standard flow under clean conditions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

import httpx

from simulator.config import settings
from simulator.fixtures.seed_users import load_users
from simulator.metrics.collector import collector
from simulator.profiles.normal_human import NormalHuman
from simulator.scenarios.admin_helper import create_test_campaign, get_admin_token, run_lottery

logger = logging.getLogger(__name__)


async def run() -> Dict[str, Any]:
    """Execute Scenario 01."""
    collector.reset()
    users = load_users()
    if len(users) < 50:
        raise ValueError(f"Need at least 50 seeded users, found {len(users)}. Run seed_users.py first.")

    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=30.0) as client:
        admin_token = await get_admin_token(client)
        campaign = await create_test_campaign(
            admin_token=admin_token,
            capacity=50,
            title="S01 Baseline: 50 Humans",
            client=client,
        )
        campaign_id = campaign.get("id") or campaign.get("campaign_id")
        logger.info(f"S01 started for campaign {campaign_id}")

        # Instantiate 50 NormalHuman clients
        clients = [
            NormalHuman(
                user_id=u["user_id"],
                token=u["token"],
                campaign_id=campaign_id,
                http_client=client,
            )
            for u in users[:50]
        ]

        # Run concurrent executions with jitter
        tasks = [c.run() for c in clients]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Run lottery
        lottery_res = await run_lottery(admin_token, campaign_id, client)
        logger.info(f"S01 lottery completed: {lottery_res}")

        # Check results
        result_tasks = [c.get_result() for c in clients]
        await asyncio.gather(*result_tasks, return_exceptions=True)

    return {
        "scenario": "s01_baseline",
        "campaign_id": campaign_id,
        "total_clients": len(clients),
        "capacity": 50,
    }
