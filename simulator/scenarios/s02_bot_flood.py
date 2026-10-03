"""Scenario 02: Bot Flood (THE MONEY SHOT)
20 NormalHuman + 40 FastBot + 20 BurstBot + 20 RetryBot, capacity 20.
Proves bots get zero advantage over normal humans under random-draw lottery.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

import httpx

from simulator.config import settings
from simulator.fixtures.seed_users import load_users
from simulator.metrics.collector import collector
from simulator.profiles.burst_bot import BurstBot
from simulator.profiles.fast_bot import FastBot
from simulator.profiles.normal_human import NormalHuman
from simulator.profiles.retry_bot import RetryBot
from simulator.scenarios.admin_helper import create_test_campaign, get_admin_token, run_lottery

logger = logging.getLogger(__name__)


async def run() -> Dict[str, Any]:
    """Execute Scenario 02."""
    collector.reset()
    users = load_users()
    if len(users) < 100:
        raise ValueError(f"Need 100 seeded users for S02, found {len(users)}. Run seed_users.py first.")

    async with httpx.AsyncClient(base_url=settings.API_BASE_URL, timeout=30.0) as client:
        admin_token = await get_admin_token(client)
        campaign = await create_test_campaign(
            admin_token=admin_token,
            capacity=20,
            title="S02 Bot Flood: 20 Humans vs 80 Bots",
            client=client,
        )
        campaign_id = campaign.get("id") or campaign.get("campaign_id")
        logger.info(f"S02 started for campaign {campaign_id}")

        clients = []
        # 20 NormalHuman (indices 0..19)
        for u in users[0:20]:
            clients.append(NormalHuman(user=u, campaign_id=campaign_id, scenario="s02_bot_flood"))

        # 40 FastBot (indices 20..59)
        for u in users[20:60]:
            clients.append(FastBot(user=u, campaign_id=campaign_id, scenario="s02_bot_flood"))

        # 20 BurstBot (indices 60..79)
        for u in users[60:80]:
            clients.append(BurstBot(user=u, campaign_id=campaign_id, scenario="s02_bot_flood"))

        # 20 RetryBot (indices 80..99)
        for u in users[80:100]:
            clients.append(RetryBot(user=u, campaign_id=campaign_id, scenario="s02_bot_flood"))

        # Launch all concurrently
        tasks = [c.run() for c in clients]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Draw lottery
        await run_lottery(admin_token, campaign_id, client)

        # Check results across all clients
        result_tasks = [c.get_result() for c in clients]
        await asyncio.gather(*result_tasks, return_exceptions=True)

    return {
        "scenario": "s02_bot_flood",
        "campaign_id": campaign_id,
        "total_clients": len(clients),
        "capacity": 20,
        "breakdown": {
            "normal_human": 20,
            "fast_bot": 40,
            "burst_bot": 20,
            "retry_bot": 20,
        },
    }
