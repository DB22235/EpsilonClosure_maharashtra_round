"""
Background worker to evaluate active campaigns and promote standby participants into released capacity.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.services.standby_service import promote_next_standby

logger = logging.getLogger(__name__)


async def process_standby_promotions(db: AsyncSession) -> dict[str, int]:
    """
    Iterates over campaigns currently in claiming state and promotes eligible
    standby queue participants into any newly available ticket capacity.
    """
    stmt = select(Campaign).where(Campaign.status.in_(["CLAIMING", "FROZEN", "ACTIVE"]))
    campaigns = list((await db.execute(stmt)).scalars().all())

    campaigns_checked = len(campaigns)
    standbys_promoted = 0

    for campaign in campaigns:
        # Attempt to promote up to available capacity
        for _ in range(5):
            res = await promote_next_standby(db, campaign.id)
            if res.get("promoted"):
                standbys_promoted += 1
            else:
                break

    logger.info(
        "Standby worker checked %d campaigns, promoted %d standbys",
        campaigns_checked,
        standbys_promoted,
    )

    return {
        "campaigns_checked": campaigns_checked,
        "standbys_promoted": standbys_promoted,
    }
