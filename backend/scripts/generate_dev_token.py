"""
Utility script to generate a signed Supabase-compatible JWT for development and testing.

Usage:
    python -m scripts.generate_dev_token
    python -m scripts.generate_dev_token --admin
    python -m scripts.generate_dev_token --sub <custom_uuid> --email test@example.com
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

# Add backend directory to sys.path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.config import lru_settings  # noqa: E402


def create_token(
    sub: str | None = None,
    email: str | None = None,
    role: str = "authenticated",
    expires_in_hours: int = 24,
) -> tuple[str, str]:
    settings = lru_settings()

    user_id = sub or str(uuid.uuid4())
    user_email = email or f"user_{user_id[:8]}@fairdrop.local"

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=expires_in_hours)

    payload = {
        "sub": user_id,
        "email": user_email,
        "role": role,
        "aud": settings.SUPABASE_JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    return token, user_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a development JWT for Fair Drop API")
    parser.add_argument("--sub", type=str, default=None, help="Specific user UUID")
    parser.add_argument("--email", type=str, default=None, help="User email")
    parser.add_argument("--admin", action="store_true", help="Seed/promote this user as ADMIN in database")
    args = parser.parse_args()

    token, user_id = create_token(sub=args.sub, email=args.email)

    print("\n" + "=" * 70)
    print("   FAIR DROP — DEVELOPMENT AUTHENTICATION TOKEN GENERATOR")
    print("=" * 70)
    print(f"\nUser UUID : {user_id}")
    if args.email:
        print(f"Email     : {args.email}")

    if args.admin:
        import asyncio
        from scripts.seed_admin import seed_admin

        print("\nPromoting user to ADMIN in PostgreSQL...")
        asyncio.run(seed_admin(uuid.UUID(user_id)))
        print("Role      : ADMIN")
    else:
        print("Role      : USER")

    print("\n" + "-" * 70)
    print("Bearer Token (Copy and paste into Swagger UI 'Authorize' button):")
    print("-" * 70)
    print(token)
    print("-" * 70 + "\n")


if __name__ == "__main__":
    main()
