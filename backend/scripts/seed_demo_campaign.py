"""
Developer CLI script to create, prepare, and publish a demo 500-seat campaign.

Usage:
    python -m scripts.seed_demo_campaign <admin_uuid>
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import async_session_factory
from app.models.participant import Profile
from app.services.campaign_service import (
    create_campaign,
    prepare_campaign,
    transition_campaign,
)


async def seed_demo_campaign(admin_id: uuid.UUID) -> None:
    """Create, prepare, and publish a 500-seat demo campaign."""
    now = datetime.now(timezone.utc)
    reg_start = now
    reg_end = now + timedelta(hours=1)
    redemption_deadline = now + timedelta(hours=3)

    async with async_session_factory() as session:
        # Verify admin exists
        stmt = select(Profile).where(Profile.id == admin_id)
        result = await session.execute(stmt)
        admin_profile = result.scalar_one_or_none()

        if admin_profile is None or admin_profile.role != "ADMIN":
            print(f"[ERROR] User {admin_id} not found or is not an ADMIN.")
            sys.exit(1)

        data = {
            "name": "Hackathon Arena Finals",
            "description": "500 seats, 50000 competitors, one fair lottery",
            "venue": "Cyber Arena",
            "capacity": 500,
            "registration_start": reg_start,
            "registration_end": reg_end,
            "redemption_deadline": redemption_deadline,
            "max_tickets_per_participant": 1,
            "allocation_method": "UNIFORM_LOTTERY",
            "standby_policy": "FIXED_ORDER",
            "policy_version": "v1.0",
        }

        request_id = "req_seed_demo_campaign"
        print("[1/3] Creating DRAFT campaign...")
        campaign = await create_campaign(session, data, admin_id, request_id)

        print("[2/3] Preparing campaign and generating 500 seats...")
        campaign = await prepare_campaign(session, campaign, admin_id, request_id)

        print("[3/3] Publishing campaign to OPEN state...")
        campaign = await transition_campaign(session, campaign, "OPEN", admin_id, request_id)

        print(f"Demo campaign created: {campaign.id}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Error: Missing admin user UUID argument.")
        print("Usage: python -m scripts.seed_demo_campaign <admin_uuid>")
        sys.exit(1)

    raw_uuid = sys.argv[1].strip()
    try:
        admin_uuid = uuid.UUID(raw_uuid)
    except ValueError:
        print(f"Error: '{raw_uuid}' is not a valid UUID string.")
        sys.exit(1)

    asyncio.run(seed_demo_campaign(admin_uuid))


if __name__ == "__main__":
    main()
