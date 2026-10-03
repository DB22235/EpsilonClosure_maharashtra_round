"""Scenario 05: Full Adversarial
All 8 client profiles running simultaneously against a live campaign.
Full stress testing under chaotic mixed adversarial traffic.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import httpx

from simulator.config import settings
from simulator.fixtures.seed_users import load_users
from simulator.metrics.collector import collector
from simulator.profiles.burst_bot import BurstBot
from simulator.profiles.direct_api_bot import DirectAPIBot
from simulator.profiles.fast_bot import FastBot
from simulator.profiles.normal_human import NormalHuman
from simulator.profiles.race_attacker import RaceAttacker
from simulator.profiles.retry_bot import RetryBot
from simulator.profiles.shared_network import SharedNetworkUser
from simulator.profiles.token_replay import TokenReplayAttacker
from simulator.scenarios.admin_helper import create_test_campaign, get_admin_token, run_lottery

logger = logging.getLogger(__name__)


async def run() -> Dict[str, Any]:
    """Execute Scenario 05."""
    collector.reset()
    users = load_users()
    if len(users) < 100:
        raise ValueError(f"Need 100 seeded users for S05, found {len(users)}. Run seed_users.py first.")

    async with httpx.AsyncClient(base_url=settings.API_BASE_URL, timeout=45.0) as client:
        admin_token = await get_admin_token(client)
        campaign = await create_test_campaign(
            admin_token=admin_token,
            capacity=30,
            title="S05 Full Adversarial Mix",
            client=client,
        )
        campaign_id = campaign.get("id") or campaign.get("campaign_id")
        logger.info(f"S05 started for campaign {campaign_id}")

        clients = []
        # Partition 100 users across 8 profiles
        # 1. 20 NormalHuman (0..19)
        for u in users[0:20]:
            clients.append(NormalHuman(user=u, campaign_id=campaign_id, scenario="s05_full_adversarial"))

        # 2. 15 SharedNetworkUser (20..34)
        for u in users[20:35]:
            clients.append(SharedNetworkUser(user=u, campaign_id=campaign_id, scenario="s05_full_adversarial"))

        # 3. 20 FastBot (35..54)
        for u in users[35:55]:
            clients.append(FastBot(user=u, campaign_id=campaign_id, scenario="s05_full_adversarial"))

        # 4. 15 BurstBot (55..69)
        for u in users[55:70]:
            clients.append(BurstBot(user=u, campaign_id=campaign_id, scenario="s05_full_adversarial"))

        # 5. 10 RetryBot (70..79)
        for u in users[70:80]:
            clients.append(RetryBot(user=u, campaign_id=campaign_id, scenario="s05_full_adversarial"))

        # 6. 5 DirectAPIBot (80..84)
        for u in users[80:85]:
            clients.append(DirectAPIBot(user=u, campaign_id=campaign_id, scenario="s05_full_adversarial"))

        # 7. 5 TokenReplayAttacker (85..89)
        for u in users[85:90]:
            clients.append(TokenReplayAttacker(user=u, campaign_id=campaign_id, scenario="s05_full_adversarial"))

        # 8. 10 RaceAttacker (90..99)
        for u in users[90:100]:
            clients.append(RaceAttacker(user=u, campaign_id=campaign_id, scenario="s05_full_adversarial"))

        # Launch all registration and attack tasks concurrently
        tasks = [c.run() for c in clients]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Run lottery
        await run_lottery(admin_token, campaign_id, client)

        # Retrieve results for all clients
        result_tasks = [c.get_result() for c in clients]
        await asyncio.gather(*result_tasks, return_exceptions=True)

    return {
        "scenario": "s05_full_adversarial",
        "campaign_id": campaign_id,
        "total_clients": len(clients),
        "capacity": 30,
    }
