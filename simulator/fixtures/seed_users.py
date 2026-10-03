"""Seed 100 test accounts in Supabase and cache their JWTs locally.

Run once before executing any scenario:
    cd simulator
    python fixtures/seed_users.py

The script is idempotent — it re-signs-in users that already exist.
Output is written to fixtures/test_users.json (gitignored).
"""

import json
import sys
from pathlib import Path

# Allow imports from simulator/ root
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client
from rich.console import Console
from rich.progress import track

from config import settings

console = Console()
CACHE_PATH = Path(__file__).parent / "test_users.json"


def seed() -> None:
    """Create/sign-in all test users and persist their JWTs."""
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    users: list[dict] = []
    failed: list[str] = []

    for i in track(range(settings.TEST_USER_COUNT), description="Seeding users..."):
        email = f"{settings.TEST_USER_PREFIX}_{i:03d}@fairdrop.local"
        password = settings.TEST_USER_PASSWORD

        # Attempt registration — silently ignore "already registered" errors
        try:
            client.auth.sign_up({"email": email, "password": password})
        except Exception:
            pass

        # Always sign in to obtain a fresh JWT
        try:
            res = client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            users.append(
                {
                    "index": i,
                    "email": email,
                    "user_id": res.user.id,
                    "access_token": res.session.access_token,
                    "refresh_token": res.session.refresh_token,
                }
            )
        except Exception as exc:
            console.print(f"[red]✗ Failed {email}: {exc}[/red]")
            failed.append(email)

    CACHE_PATH.write_text(json.dumps(users, indent=2), encoding="utf-8")
    console.print(
        f"\n[bold green]✅ Seeded {len(users)} users → {CACHE_PATH}[/bold green]"
    )
    if failed:
        console.print(f"[yellow]⚠ {len(failed)} users failed: {failed[:5]}...[/yellow]")


def load_users() -> list[dict]:
    """Load cached test users from disk. Raises if seed hasn't been run."""
    if not CACHE_PATH.exists():
        raise FileNotFoundError(
            f"{CACHE_PATH} not found.\n"
            "Run: python fixtures/seed_users.py"
        )
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    seed()
