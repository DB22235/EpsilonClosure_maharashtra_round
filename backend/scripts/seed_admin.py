"""
Developer CLI script to seed or promote a user profile to ADMIN role.

Usage:
    python -m scripts.seed_admin <supabase_user_uuid>
"""

from __future__ import annotations

import asyncio
import sys
import uuid

from sqlalchemy import select

from app.database import async_session_factory
from app.models.participant import Participant, Profile
from app.security.hashing import hash_email


async def seed_admin(user_id: uuid.UUID) -> None:
    """Promote or create an admin profile for the given user UUID."""
    async with async_session_factory() as session:
        # Check if profile exists
        stmt = select(Profile).where(Profile.id == user_id)
        result = await session.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile is not None:
            profile.role = "ADMIN"
            print(f"[OK] Existing profile found. Updated role to 'ADMIN' for user ID: {user_id}")
        else:
            profile = Profile(
                id=user_id,
                display_name="Admin",
                role="ADMIN",
                email_verified=True,
            )
            session.add(profile)
            print(f"[OK] Created new profile with 'ADMIN' role for user ID: {user_id}")

        await session.flush()

        # Check or create linked participant
        p_stmt = select(Participant).where(Participant.account_id == user_id)
        p_result = await session.execute(p_stmt)
        participant = p_result.scalar_one_or_none()

        if participant is None:
            new_participant = Participant(
                account_id=user_id,
                email_hash=hash_email("admin@fairdrop.local"),
                verification_status="VERIFIED",
                risk_level="LOW",
            )
            session.add(new_participant)
            print(f"[OK] Created linked participant record for admin user ID: {user_id}")

        await session.commit()
        print(f"[SUCCESS] User {user_id} is now an ADMIN in Fair Drop.")


def main() -> None:
    if len(sys.argv) < 2:
        print("Error: Missing Supabase user UUID argument.")
        print("Usage: python -m scripts.seed_admin <supabase_user_uuid>")
        sys.exit(1)

    raw_uuid = sys.argv[1].strip()
    try:
        user_uuid = uuid.UUID(raw_uuid)
    except ValueError:
        print(f"Error: '{raw_uuid}' is not a valid UUID string.")
        sys.exit(1)

    asyncio.run(seed_admin(user_uuid))


if __name__ == "__main__":
    main()
