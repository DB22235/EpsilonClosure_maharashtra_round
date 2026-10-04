"""
User Creation CLI Utility.

Allows creating a verified Normal User or Admin User with custom credentials.

Usage:
    python -m scripts.create_user --email user@example.com --password SecretPassword123!
    python -m scripts.create_user --email admin@example.com --password SecretPassword123! --role ADMIN
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import httpx
from sqlalchemy import select, text

from app.config import lru_settings
from app.database import async_session_factory
from app.models.participant import Participant, Profile
from app.security.hashing import hash_email


async def create_user(email: str, password: str, role: str = "USER", display_name: str | None = None) -> None:
    settings = lru_settings()
    supabase_url = settings.SUPABASE_URL
    anon_key = settings.SUPABASE_ANON_KEY

    print("=" * 65)
    print(f"Creating FairDrop User: {email} (Role: {role})")
    print("=" * 65)

    # 1. Sign up user via Supabase Auth API
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            signup_res = await client.post(
                f"{supabase_url}/auth/v1/signup",
                headers={"apikey": anon_key, "Content-Type": "application/json"},
                json={"email": email, "password": password},
            )
        except Exception as e:
            print(f"[ERROR] Failed to reach Supabase Auth API: {e}")
            return

    if signup_res.status_code not in (200, 201):
        err_body = signup_res.text
        if "already registered" in err_body.lower() or "user already exists" in err_body.lower():
            print(f"[INFO] User {email} already exists in Supabase Auth. Updating role and status...")
        else:
            print(f"[ERROR] Supabase Auth returned status {signup_res.status_code}: {err_body}")
            return

    # 2. Query user ID from auth.users and auto-confirm email
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT id, email FROM auth.users WHERE lower(email) = lower(:email);"),
            {"email": email.strip()},
        )
        row = result.fetchone()

        if not row:
            print(f"[ERROR] User ID for {email} could not be resolved from auth.users.")
            return

        user_id = row.id
        print(f"[OK] Supabase Auth user resolved (UUID: {user_id})")

        # Auto-confirm email
        await session.execute(
            text("UPDATE auth.users SET email_confirmed_at = COALESCE(email_confirmed_at, NOW()) WHERE id = :id;"),
            {"id": user_id},
        )
        print("[OK] Confirmed email in auth.users")

        # 3. Create or update Profile
        name = display_name or email.split("@")[0].capitalize()
        prof_res = await session.execute(select(Profile).where(Profile.id == user_id))
        profile = prof_res.scalar_one_or_none()

        if profile is not None:
            profile.role = role.upper()
            profile.display_name = name
            profile.email_verified = True
            print(f"[OK] Updated existing profile to role '{role.upper()}'")
        else:
            profile = Profile(
                id=user_id,
                display_name=name,
                role=role.upper(),
                email_verified=True,
            )
            session.add(profile)
            print(f"[OK] Created new profile with role '{role.upper()}'")

        await session.flush()

        # 4. Create or update Participant
        part_res = await session.execute(select(Participant).where(Participant.account_id == user_id))
        participant = part_res.scalar_one_or_none()

        if participant is None:
            new_part = Participant(
                account_id=user_id,
                email_hash=hash_email(email),
                verification_status="VERIFIED",
                risk_level="LOW",
            )
            session.add(new_part)
            print("[OK] Created linked participant record")

        await session.commit()

        print("\n" + "=" * 65)
        print(f"[SUCCESS] User '{email}' created successfully as {role.upper()}!")
        print("=" * 65)
        if role.upper() == "ADMIN":
            print("Sign in at: http://localhost:3000/admin/login")
        else:
            print("Sign in at: http://localhost:3000/login")
        print("=" * 65 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a FairDrop user directly.")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--password", required=True, help="User password (min 6 characters)")
    parser.add_argument("--role", default="USER", choices=["USER", "ADMIN"], help="Account role (USER or ADMIN)")
    parser.add_argument("--name", help="Display name for profile")

    args = parser.parse_args()
    asyncio.run(create_user(email=args.email, password=args.password, role=args.role, display_name=args.name))


if __name__ == "__main__":
    main()
