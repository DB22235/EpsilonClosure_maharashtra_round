"""
Seed standard demo accounts (Admin and Participant) for local/staging environments.

Usage:
    python -m scripts.seed_demo_accounts
"""

from __future__ import annotations

import asyncio
import json
import uuid

import httpx
from sqlalchemy import select, text

from app.config import lru_settings
from app.database import async_session_factory
from app.models.participant import Participant, Profile
from app.security.hashing import hash_email

USERS_TO_CREATE = [
    {
        "email": "admin@fairdrop.com",
        "password": "AdminPassword123!",
        "role": "ADMIN",
        "display_name": "Admin Operator",
    },
    {
        "email": "user@fairdrop.com",
        "password": "UserPassword123!",
        "role": "USER",
        "display_name": "Test User",
    },
    {
        "email": "ntc3108@gmail.com",
        "password": "Password123!",
        "role": "ADMIN",
        "display_name": "Naman",
    },
]


async def provision_user(u: dict) -> None:
    email = u["email"].strip().lower()
    password = u["password"]
    role = u["role"].upper()
    display_name = u["display_name"]
    inst_id = uuid.UUID(int=0)

    async with async_session_factory() as session:
        # Check if already exists in auth.users
        res = await session.execute(
            text("SELECT id FROM auth.users WHERE lower(email) = lower(:email);"),
            {"email": email},
        )
        row = res.fetchone()

        if row:
            user_id = row.id
            # Update password and confirm email
            await session.execute(
                text(
                    "UPDATE auth.users SET encrypted_password = crypt(:pwd, gen_salt('bf')), "
                    "email_confirmed_at = NOW() WHERE id = :id;"
                ),
                {"pwd": password, "id": user_id},
            )
        else:
            user_id = uuid.uuid4()
            user_meta = json.dumps(
                {"sub": str(user_id), "email": email, "email_verified": False, "phone_verified": False}
            )
            app_meta = json.dumps({"provider": "email", "providers": ["email"]})

            stmt = text("""
                INSERT INTO auth.users (
                    id, instance_id, aud, role, email, encrypted_password,
                    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
                    confirmation_token, recovery_token, email_change_token_new,
                    email_change, phone_change, phone_change_token,
                    email_change_token_current, reauthentication_token,
                    created_at, updated_at
                ) VALUES (
                    :id, :instance_id, 'authenticated', 'authenticated', :email,
                    crypt(:password, gen_salt('bf')), NOW(),
                    cast(:app_meta as jsonb), cast(:user_meta as jsonb),
                    '', '', '', '', '', '', '', '', NOW(), NOW()
                );
            """)
            await session.execute(
                stmt,
                {
                    "id": user_id,
                    "instance_id": inst_id,
                    "email": email,
                    "password": password,
                    "app_meta": app_meta,
                    "user_meta": user_meta,
                },
            )

            ident_stmt = text("""
                INSERT INTO auth.identities (
                    id, user_id, identity_data, provider, provider_id,
                    last_sign_in_at, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), :user_id, cast(:user_meta as jsonb),
                    'email', :provider_id, NOW(), NOW(), NOW()
                );
            """)
            await session.execute(
                ident_stmt,
                {"user_id": user_id, "user_meta": user_meta, "provider_id": str(user_id)},
            )

        # Provision or update Profile
        prof_res = await session.execute(select(Profile).where(Profile.id == user_id))
        prof = prof_res.scalar_one_or_none()
        if prof:
            prof.role = role
            prof.display_name = display_name
            prof.email_verified = True
        else:
            prof = Profile(
                id=user_id,
                display_name=display_name,
                role=role,
                email_verified=True,
            )
            session.add(prof)

        await session.flush()

        # Provision or update Participant
        part_res = await session.execute(select(Participant).where(Participant.account_id == user_id))
        part = part_res.scalar_one_or_none()
        if not part:
            part = Participant(
                account_id=user_id,
                email_hash=hash_email(email),
                verification_status="VERIFIED",
                risk_level="LOW",
            )
            session.add(part)

        await session.commit()
        print(f"[OK] Successfully provisioned: {email} | Role: {role}")


async def main() -> None:
    settings = lru_settings()
    print("Provisioning accounts...")
    for u in USERS_TO_CREATE:
        await provision_user(u)

    print("\nVerifying GoTrue logins for all accounts:")
    url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        for u in USERS_TO_CREATE:
            try:
                res = await client.post(
                    url,
                    headers=headers,
                    json={"email": u["email"], "password": u["password"]},
                )
                status_str = "SUCCESS (200)" if res.status_code == 200 else f"FAILED ({res.status_code})"
                print(f" -> {u['email']}: {status_str}")
            except Exception as ex:
                print(f" -> {u['email']}: Network error ({ex})")


if __name__ == "__main__":
    asyncio.run(main())
