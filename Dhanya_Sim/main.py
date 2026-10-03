"""Dhanya_Sim — Fair Drop Adversarial Simulation Runner.

CLI entry point for running simulation scenarios against a live or mock
Fair Drop API. Supports multiple named scenarios with configurable parameters.

Usage:
    # Activate the venv first
    source .venv/bin/activate

    # Run baseline human scenario
    python main.py --scenario normal_human --campaign camp_001 --participants 200

    # Run burst-bot mixed scenario
    python main.py --scenario burst_bot --campaign camp_001 --bots 50 --humans 200

    # Run full mixed-population judge demo
    python main.py --scenario mixed_demo --campaign camp_001

    # Override API URL
    python main.py --scenario mixed_demo --campaign camp_001 --url http://localhost:8000
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from scenarios import (
    ScenarioConfig,
    NormalHumanScenario,
    BurstBotScenario,
    MixedDemoScenario,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("dhanya_sim.main")

SCENARIOS = {
    "normal_human": NormalHumanScenario,
    "burst_bot": BurstBotScenario,
    "mixed_demo": MixedDemoScenario,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dhanya_sim",
        description="Fair Drop — Adversarial Simulation Runner",
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default="mixed_demo",
        help="Scenario to run (default: mixed_demo).",
    )
    parser.add_argument(
        "--campaign",
        default="campaign_demo_001",
        help="Campaign ID to target (default: campaign_demo_001).",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Fair Drop API base URL (default: http://localhost:8000).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=50,
        help="Maximum concurrent HTTP workers (default: 50).",
    )
    parser.add_argument(
        "--capacity",
        type=int,
        default=500,
        help="Campaign seat capacity for integrity assertions (default: 500).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-request HTTP timeout in seconds (default: 10.0).",
    )
    parser.add_argument(
        "--ramp",
        type=float,
        default=5.0,
        dest="ramp_seconds",
        help="Warm-up ramp duration in seconds (default: 5.0).",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Output directory for JSON/CSV reports (default: output/).",
    )
    parser.add_argument(
        "--participants",
        type=int,
        default=200,
        help="[normal_human] Number of human participants (default: 200).",
    )
    parser.add_argument(
        "--bots",
        type=int,
        default=50,
        help="[burst_bot] Number of bot identities (default: 50).",
    )
    parser.add_argument(
        "--humans",
        type=int,
        default=200,
        help="[burst_bot] Number of human identities (default: 200).",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    Path(args.output).mkdir(parents=True, exist_ok=True)

    config = ScenarioConfig(
        campaign_id=args.campaign,
        base_url=args.url,
        capacity=args.capacity,
        concurrency=args.concurrency,
        timeout=args.timeout,
        ramp_seconds=args.ramp_seconds,
        output_dir=args.output,
    )

    scenario_class = SCENARIOS[args.scenario]
    scenario_kwargs: dict = {"config": config}

    if args.scenario == "normal_human":
        scenario_kwargs["num_participants"] = args.participants
    elif args.scenario == "burst_bot":
        scenario_kwargs["num_bots"] = args.bots
        scenario_kwargs["num_humans"] = args.humans

    logger.info(
        "Starting scenario '%s' → campaign=%s url=%s",
        args.scenario,
        args.campaign,
        args.url,
    )

    scenario = scenario_class(**scenario_kwargs)
    scenario.setup()
    await scenario.run()

    results = scenario.report()
    if results:
        integrity = results.get("integrity", {})
        passed = integrity.get("invariants_passed", False)
        if passed:
            logger.info("✅  All integrity invariants passed.")
            sys.exit(0)
        else:
            logger.error("❌  One or more integrity invariants FAILED.")
            sys.exit(1)
    else:
        logger.warning("No results collected — check that the API server is reachable.")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
