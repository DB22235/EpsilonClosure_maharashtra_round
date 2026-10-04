"""
Manual CLI trigger script for background worker execution.

Usage:
    python -m scripts.run_workers_once
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from dotenv import load_dotenv

load_dotenv(dotenv_path=backend_root / ".env")

from app.workers.runner import run_all_once

# Configure standard console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main() -> None:
    print("Executing background worker cycle...")
    result = await run_all_once()
    print("\nWorker Execution Results:")
    print(json.dumps(result, indent=2))

    if not result.get("all_successful", False):
        print("\n[WARNING] Some worker jobs encountered errors. Review logs above.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All worker jobs completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
