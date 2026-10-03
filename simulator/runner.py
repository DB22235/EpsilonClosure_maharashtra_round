"""CLI Runner for executing live adversarial simulation scenarios against Dhruv's FastAPI backend."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Callable, Dict

from simulator.metrics.analyzer import analyze
from simulator.metrics.collector import collector
from simulator.metrics.reporter import write_reports
from simulator.scenarios import (
    s01_baseline,
    s02_bot_flood,
    s03_replay_attack,
    s04_race_condition,
    s05_full_adversarial,
    s06_cutoff_boundary,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("simulator.runner")

SCENARIOS: Dict[str, Callable] = {
    "s01": s01_baseline.run,
    "s01_baseline": s01_baseline.run,
    "s02": s02_bot_flood.run,
    "s02_bot_flood": s02_bot_flood.run,
    "s03": s03_replay_attack.run,
    "s03_replay_attack": s03_replay_attack.run,
    "s04": s04_race_condition.run,
    "s04_race_condition": s04_race_condition.run,
    "s05": s05_full_adversarial.run,
    "s05_full_adversarial": s05_full_adversarial.run,
    "s06": s06_cutoff_boundary.run,
    "s06_cutoff_boundary": s06_cutoff_boundary.run,
}


async def run_scenario(name: str):
    """Run an individual scenario, analyze metrics, and generate reports."""
    func = SCENARIOS.get(name)
    if not func:
        logger.error(f"Unknown scenario: {name}. Use --list to view valid scenarios.")
        sys.exit(1)

    logger.info(f"=== Starting Scenario: {name} ===")
    meta = await func()
    raw = collector.get_all()
    analysis = analyze(collector, meta)
    paths = write_reports(analysis, raw)

    logger.info(f"=== Scenario {name} Complete ===")
    logger.info(f"Bot Advantage Ratio: {analysis.get('bot_advantage_ratio')}x")
    logger.info(f"Total Requests: {analysis.get('total_requests')}")
    logger.info(f"Reports: JSON={paths['json']}, Markdown={paths['markdown']}")


async def main():
    parser = argparse.ArgumentParser(description="Fair Drop Live Adversarial Simulator")
    parser.add_argument(
        "--scenario", "-s",
        type=str,
        help="Scenario to execute (e.g. s01, s02_bot_flood)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all scenarios sequentially",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all registered scenarios",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed 100 test user accounts in Supabase",
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable Scenarios:")
        print("  - s01 (s01_baseline): 50 Humans, 50 capacity, clean baseline")
        print("  - s02 (s02_bot_flood): 20 Humans + 80 Bots, capacity 20 (THE MONEY SHOT)")
        print("  - s03 (s03_replay_attack): Token replay with fresh idempotency keys")
        print("  - s04 (s04_race_condition): 10 parallel hold claims on entitlement")
        print("  - s05 (s05_full_adversarial): All 8 profiles concurrent stress mix")
        print("  - s06 (s06_cutoff_boundary): Boundary cutoff before/after close")
        return

    if args.seed:
        from simulator.fixtures.seed_users import seed_users
        logger.info("Seeding 100 users in Supabase...")
        await seed_users(count=100)
        logger.info("Seeding complete.")
        return

    if args.all:
        for s_name in ["s01", "s02", "s03", "s04", "s05", "s06"]:
            await run_scenario(s_name)
        return

    if args.scenario:
        await run_scenario(args.scenario)
        return

    parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
