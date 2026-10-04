"""
Admin Role Elevation CLI Tool.

Allows promoting any user registered via Supabase (/signup) to the ADMIN role.

Usage:
    python -m scripts.promote_admin --email <user_email>
    python -m scripts.promote_admin --uuid <user_uuid>
    python -m scripts.promote_admin --list
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from sqlalchemy import select, text

from app.database import async_session_factory
from app.models.participant import Participant, Profile
from app.security.hashing import hash_email


async def list_users() -> None:
    async with async_session_factory() as session:
        auth_users = (
            await session.execute(
                text("SELECT id, email, created_at FROM auth.users ORDER BY created_at DESC;")
            )
        ).fetchall()

        if not auth_users:
            print("\n[INFO] No accounts found in auth.users.")
            print("To create an account, open http://localhost:3000/signup and register.")
            return

        print("\nRegistered Accounts:")
        print("-" * 75)
        print(f"{'Email':<30} | {'Role':<10} | {'User ID'}")
        print("-" * 75)

        for u in auth_users:
            prof = (
                await session.execute(select(Profile).where(Profile.id == u.id))
            ).scalar_one_or_none()
            role = prof.role if prof else "NO_PROFILE (Default: USER)"
            print(f"{str(u.email):<30} | {role:<10} | {u.id}")
        print("-" * 75)


async def promote_user(email: str | None = None, user_uuid: uuid.UUID | None = None) -> bool:
    async with async_session_factory() as session:
        target_id: uuid.UUID | None = user_uuid
        target_email: str | None = email

        if target_id is None and target_email is not None:
            # Query auth.users for this email
            result = await session.execute(
                text("SELECT id, email FROM auth.users WHERE lower(email) = lower(:email);"),
                {"email": target_email.strip()},
            )
            row = result.fetchone()
            if row is None:
                print(f"\n[ERROR] No account found with email '{target_email}' in auth.users.")
                print("Make sure you registered this email first at http://localhost:3000/signup")
                await list_users()
                return False
            target_id = row.id
            target_email = row.email
        elif target_id is not None:
            result = await session.execute(
                text("SELECT email FROM auth.users WHERE id = :id;"),
                {"id": str(target_id)},
            )
            row = result.fetchone()
            if row is not None:
                target_email = row.email

        # Auto-confirm user email in Supabase auth.users if not already confirmed
        await session.execute(
            text("UPDATE auth.users SET email_confirmed_at = COALESCE(email_confirmed_at, NOW()) WHERE id = :id;"),
            {"id": target_id},
        )

        # 1. Update or create Profile with role ADMIN
        prof_stmt = select(Profile).where(Profile.id == target_id)
        prof_res = await session.execute(prof_stmt)
        profile = prof_res.scalar_one_or_none()

        display_name = target_email.split("@")[0].capitalize() if target_email else "Admin"

        if profile is not None:
            profile.role = "ADMIN"
            print(f"[OK] Updated existing profile for user {target_id} to role 'ADMIN'")
        else:
            profile = Profile(
                id=target_id,
                display_name=display_name,
                role="ADMIN",
                email_verified=True,
            )
            session.add(profile)
            print(f"[OK] Provisioned new profile for user {target_id} with role 'ADMIN'")

        await session.flush()

        # 2. Ensure Participant record exists
        part_stmt = select(Participant).where(Participant.account_id == target_id)
        part_res = await session.execute(part_stmt)
        participant = part_res.scalar_one_or_none()

        if participant is None:
            new_part = Participant(
                account_id=target_id,
                email_hash=hash_email(target_email) if target_email else "",
                verification_status="VERIFIED",
                risk_level="LOW",
            )
            session.add(new_part)
            print(f"[OK] Provisioned linked participant record for user {target_id}")

        await session.commit()

        print("\n" + "=" * 60)
        print(f"[SUCCESS] User '{target_email or target_id}' is now an ADMIN!")
        print("=" * 60)
        print("You can now sign in to the operator console at:")
        print("  http://localhost:3000/admin/login")
        print("=" * 60 + "\n")
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a FairDrop user to ADMIN role.")
    parser.add_argument("--email", help="Email of the registered user to promote")
    parser.add_argument("--uuid", help="UUID of the registered user to promote")
    parser.add_argument("--list", action="store_true", help="List all accounts in the database")

    args = parser.parse_args()

    if args.list or (not args.email and not args.uuid):
        asyncio.run(list_users())
        if not args.list:
            print("\nUsage example:")
            print("  python -m scripts.promote_admin --email admin@example.com")
        return

    target_uuid = None
    if args.uuid:
        try:
            target_uuid = uuid.UUID(args.uuid.strip())
        except ValueError:
            print(f"[ERROR] '{args.uuid}' is not a valid UUID format.")
            sys.exit(1)

    asyncio.run(promote_user(email=args.email, user_uuid=target_uuid))


if __name__ == "__main__":
    main()
