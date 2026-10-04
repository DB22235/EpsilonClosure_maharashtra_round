"""
Supabase JWT Fetcher Script.

Authenticates a Supabase user with email and password via Supabase Auth API
and prints the resulting access_token for use in Swagger UI (/docs) or API requests.

Usage:
    python -m scripts.get_supabase_token
"""

from __future__ import annotations

import asyncio
import getpass
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Ensure apps/backend root is on sys.path and load .env
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))
load_dotenv(dotenv_path=backend_root / ".env")

# ANSI color codes
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_CYAN = "\033[96m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"


async def fetch_token() -> None:
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

    if not supabase_url or not supabase_anon_key:
        print(
            f"{COLOR_RED}{COLOR_BOLD}[ERROR] SUPABASE_ANON_KEY or SUPABASE_URL is missing!{COLOR_RESET}\n"
            f"{COLOR_RED}Please configure them in your .env file:\n"
            f"  1. Go to your Supabase Dashboard (https://supabase.com/dashboard)\n"
            f"  2. Open your project -> Settings -> API\n"
            f"  3. Under 'Project API keys', copy the 'anon' (public) key\n"
            f"  4. Add this line to backend/.env:\n"
            f"       SUPABASE_ANON_KEY=<your-anon-public-key>{COLOR_RESET}\n"
        )
        sys.exit(1)

    print(f"{COLOR_CYAN}{COLOR_BOLD}=== Supabase JWT Auth Token Generator ==={COLOR_RESET}")
    print(f"Target URL: {supabase_url}\n")

    email = input("Supabase Test Email: ").strip()
    if not email:
        print(f"{COLOR_RED}[ERROR] Email cannot be empty.{COLOR_RESET}")
        sys.exit(1)

    password = getpass.getpass("Supabase Test Password: ").strip()
    if not password:
        print(f"{COLOR_RED}[ERROR] Password cannot be empty.{COLOR_RESET}")
        sys.exit(1)

    token_url = f"{supabase_url.rstrip('/')}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": supabase_anon_key,
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "password": password,
    }

    print(f"\n{COLOR_CYAN}Authenticating with Supabase Auth API...{COLOR_RESET}")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(token_url, headers=headers, json=payload)
    except Exception as exc:
        print(f"{COLOR_RED}{COLOR_BOLD}[ERROR] Network request failed: {exc}{COLOR_RESET}")
        sys.exit(1)

    if response.status_code == 200:
        data = response.json()
        access_token = data.get("access_token", "")
        user_info = data.get("user", {})
        user_id = user_info.get("id", "unknown")
        user_email = user_info.get("email", email)

        print(f"\n{COLOR_GREEN}{COLOR_BOLD}[SUCCESS] Authenticated successfully!{COLOR_RESET}")
        print(f"User ID:    {user_id}")
        print(f"User Email: {user_email}")
        print(f"Expires In: {data.get('expires_in', 3600)}s")
        print(
            f"\n{COLOR_GREEN}{COLOR_BOLD}"
            f"================================================================================\n"
            f"COPY THIS INTO SWAGGER AUTHORIZE BOX:\n"
            f"--------------------------------------------------------------------------------\n"
            f"{access_token}\n"
            f"================================================================================\n"
            f"{COLOR_RESET}"
        )
        print(
            f"{COLOR_CYAN}Instructions:\n"
            f"  1. Open http://localhost:8000/docs in your browser\n"
            f"  2. Click the green 'Authorize' button (top right)\n"
            f"  3. Paste the token above directly into the 'Value' field (do NOT add 'Bearer')\n"
            f"  4. Click 'Authorize' then 'Close'\n"
            f"  5. Test GET /api/v1/auth/me to verify your live authenticated identity!{COLOR_RESET}\n"
        )
    else:
        print(
            f"\n{COLOR_RED}{COLOR_BOLD}[ERROR] Supabase Auth Error (HTTP {response.status_code}):{COLOR_RESET}\n"
            f"{COLOR_RED}{response.text}{COLOR_RESET}\n"
        )
        sys.exit(1)


def main() -> None:
    asyncio.run(fetch_token())


if __name__ == "__main__":
    main()
