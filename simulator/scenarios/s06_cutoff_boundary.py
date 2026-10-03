"""Scenario 06: Cutoff Boundary
Registration window ends in 5 seconds.
Clients register right before and right after cutoff.
Expectation: Requests arriving before cutoff succeed (200), requests after cutoff rejected (400/409 Window Closed).
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
from simulator.scenarios.admin_helper import create_test_campaign, get_admin_token

logger = logging.getLogger(__name__)


async def run() -> Dict[str, Any]:
    """Execute Scenario 06."""
    collector.reset()
    users = load_users()
    if len(users) < 20:
        raise ValueError("Need at least 20 seeded users. Run seed_users.py first.")

    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=30.0) as client:
        admin_token = await get_admin_token(client)
        # Create campaign with ultra-short registration duration or manually trigger close
        campaign = await create_test_campaign(
            admin_token=admin_token,
            capacity=10,
            title="S06 Cutoff Boundary",
            duration_minutes=1,
            client=client,
        )
        campaign_id = campaign.get("id") or campaign.get("campaign_id")
        logger.info(f"S06 started for campaign {campaign_id}")

        early_users = [
            NormalHuman(u["user_id"], u["token"], campaign_id, http_client=client)
            for u in users[:10]
        ]
        late_users = [
            NormalHuman(u["user_id"], u["token"], campaign_id, http_client=client)
            for u in users[10:20]
        ]

        # Early users register immediately
        await asyncio.gather(*[u.run() for u in early_users], return_exceptions=True)

        # Close the registration window via admin endpoint
        headers = {"Authorization": f"Bearer {admin_token}"}
        try:
            await client.post(f"/api/v1/admin/campaigns/{campaign_id}/close", headers=headers)
        except Exception as e:
            logger.warning(f"Error closing registration window: {e}")

        # Late users attempt to register after cutoff
        await asyncio.gather(*[u.run() for u in late_users], return_exceptions=True)

    return {
        "scenario": "s06_cutoff_boundary",
        "campaign_id": campaign_id,
        "early_clients": len(early_users),
        "late_clients": len(late_users),
    }
