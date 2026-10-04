"""
Database Reset & Test Data Purge Utility.

Cleans all test data from FairDrop tables and Supabase auth.users,
leaving database tables, schemas, constraints, and Alembic migrations intact.

Usage:
    python -m scripts.reset_database
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from app.database import async_session_factory


async def reset_database() -> None:
    print("=" * 60)
    print("FairDrop Database Reset & Test Data Purge")
    print("=" * 60)

    tables_to_purge = [
        "bookings",
        "entitlements",
        "seats",
        "lottery_entries",
        "lottery_runs",
        "registrations",
        "idempotency_records",
        "audit_events",
        "campaigns",
        "participants",
        "profiles",
    ]

    async with async_session_factory() as session:
        print("\n[1/3] Counting records prior to purge...")
        for table in tables_to_purge:
            try:
                res = await session.execute(text(f"SELECT COUNT(*) FROM public.{table};"))
                count = res.scalar()
                print(f"  - public.{table}: {count} records")
            except Exception as e:
                print(f"  - public.{table}: (table check skipped: {e})")

        try:
            auth_res = await session.execute(text("SELECT COUNT(*) FROM auth.users;"))
            auth_count = auth_res.scalar()
            print(f"  - auth.users: {auth_count} accounts")
        except Exception as e:
            print(f"  - auth.users: (auth check skipped: {e})")

        print("\n[2/3] Executing complete data purge...")
        for table in tables_to_purge:
            try:
                await session.execute(text(f"DELETE FROM public.{table};"))
                print(f"  [OK] Purged public.{table}")
            except Exception as e:
                print(f"  [ERROR] Failed to purge public.{table}: {e}")

        # Purge Supabase Auth users
        try:
            await session.execute(text("DELETE FROM auth.users;"))
            print("  [OK] Purged auth.users (all Supabase authentication accounts)")
        except Exception as e:
            print(f"  [NOTICE] auth.users purge: {e}")

        await session.commit()
        print("\n[3/3] Verifying clean zero-state across all tables...")

        all_clean = True
        for table in tables_to_purge:
            try:
                res = await session.execute(text(f"SELECT COUNT(*) FROM public.{table};"))
                count = res.scalar()
                if count != 0:
                    print(f"  [FAIL] public.{table} still has {count} rows!")
                    all_clean = False
                else:
                    print(f"  [OK] public.{table}: 0 rows")
            except Exception as e:
                print(f"  [ERROR] public.{table}: {e}")

        try:
            auth_res = await session.execute(text("SELECT COUNT(*) FROM auth.users;"))
            auth_count = auth_res.scalar()
            if auth_count != 0:
                print(f"  [FAIL] auth.users still has {auth_count} rows!")
                all_clean = False
            else:
                print(f"  [OK] auth.users: 0 accounts")
        except Exception as e:
            print(f"  [ERROR] auth.users check: {e}")

        print("=" * 60)
        if all_clean:
            print(">>> SUCCESS: Database is 100% clean and ready for fresh user testing. <<<")
        else:
            print(">>> WARNING: Some records could not be purged. Check errors above. <<<")
        print("=" * 60)


def main() -> None:
    asyncio.run(reset_database())


if __name__ == "__main__":
    main()
