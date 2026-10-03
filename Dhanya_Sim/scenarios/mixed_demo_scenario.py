"""Full mixed-population demo scenario for Fair Drop.

The flagship scenario simulating all 10 client profile types simultaneously
at realistic ratios: 500 seats / ~50,000 simulated participants spread across
legitimate humans, various bot types, and edge-case profiles.

This scenario is designed to be run against the live Fair Drop backend for
the judge demonstration run.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from .base_scenario import BaseScenario, ScenarioConfig
from ..runner.engine import SimulationEngine
from ..profiles.normal_human import NormalHuman
from ..profiles.fast_bot import FastBot
from ..profiles.burst_bot import BurstBot
from ..profiles.retry_bot import RetryBot
from ..profiles.account_farm import AccountFarm
from ..profiles.direct_api_bot import DirectAPIBot as DirectApiBot
from ..profiles.token_replay_attacker import TokenReplayAttacker
from ..profiles.race_condition_attacker import RaceConditionAttacker
from ..profiles.shared_network_user import SharedNetworkUser
from ..profiles.slow_accessibility_user import SlowAccessibilityUser

logger = logging.getLogger(__name__)


# Population ratio: (profile_class, count, is_adversarial_label)
_POPULATION_SPEC = [
    (NormalHuman,            300, False),
    (SlowAccessibilityUser,   50, False),
    (SharedNetworkUser,       30, False),
    (FastBot,                 80, True),
    (BurstBot,                40, True),
    (RetryBot,                20, True),
    (AccountFarm,             20, True),
    (DirectApiBot,            15, True),
    (TokenReplayAttacker,     10, True),
    (RaceConditionAttacker,   10, True),
]


class MixedDemoScenario(BaseScenario):
    """Scenario: full mixed-population judge demonstration.

    Simulates all 10 client profile types simultaneously with realistic
    population ratios.  The goal is to produce evidence that:

    - Legitimate users and benign edge-cases (slow, shared-network) are
      NOT blocked or penalised relative to bots.
    - Bot win rates vs valid entries do not significantly exceed human rates.
    - All integrity invariants pass: zero oversell, zero duplicate allocation,
      zero successful replay attacks.
    - A rich, exportable metrics report is produced for the dashboard.
    """

    name = "mixed_demo"
    description = (
        "Full mixed-population demo: all 10 client profiles, ~575 total workers. "
        "Produces judge-ready fairness, integrity, and reliability evidence."
    )

    def setup(self) -> None:
        """Generate identity lists for all population segments."""
        self._populations: List[Dict[str, Any]] = []
        global_idx = 0
        for profile_class, count, _ in _POPULATION_SPEC:
            ids = [
                self._make_identity(
                    global_idx + i,
                    prefix=profile_class.profile_type,
                )
                for i in range(count)
            ]
            self._populations.append({
                "profile_class": profile_class,
                "identities": ids,
            })
            global_idx += count

        total = sum(len(p["identities"]) for p in self._populations)
        self.identities = [
            identity
            for p in self._populations
            for identity in p["identities"]
        ]
        logger.info(
            "MixedDemoScenario setup: %d total workers across %d profile types for campaign %s",
            total,
            len(self._populations),
            self.config.campaign_id,
        )

    async def run(self) -> None:
        """Execute the full mixed-population demo scenario."""
        engine_config = self._build_engine_config()
        async with SimulationEngine(config=engine_config) as engine:
            await engine.run_mixed_scenario(
                populations=self._populations,
                campaign_id=self.config.campaign_id,
            )
            summary = engine.collector.summarize()
            engine.collector.export_json(
                f"{self.config.output_dir}/{self.name}_metrics.json"
            )
            engine.collector.export_csv(
                f"{self.config.output_dir}/{self.name}_records.csv"
            )
            engine.collector.print_summary()

        self._results = summary
        self._log_judge_assertions(summary)

    def _log_judge_assertions(self, summary: Dict[str, Any]) -> None:
        """Log pass/fail status for each judge-critical invariant."""
        integrity = summary.get("integrity", {})
        fairness = summary.get("fairness", {})
        reliability = summary.get("reliability", {})

        checks = [
            (
                "Oversell = 0",
                integrity.get("oversell_violations", -1) == 0,
            ),
            (
                "Duplicate allocation = 0",
                integrity.get("duplicate_allocation_violations", -1) == 0,
            ),
            (
                "Replay attack success = 0",
                integrity.get("replay_attack_successes", -1) == 0,
            ),
            (
                "Confirmed seats <= capacity",
                integrity.get("confirmed_seats", 9999)
                <= integrity.get("capacity", self.config.capacity),
            ),
            (
                "Bot advantage ratio < 1.1",
                (fairness.get("bot_advantage_ratio") or 0) < 1.1,
            ),
            (
                "False positive rate (benign clients) < 10%",
                reliability.get("false_positive_rate_benign_clients", 1.0) < 0.10,
            ),
        ]

        logger.info("=== Judge Assertion Results ===")
        all_passed = True
        for label, passed in checks:
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False
            logger.info("  [%s] %s", status, label)

        if all_passed:
            logger.info("ALL INVARIANTS PASSED — simulation evidence is judge-ready.")
        else:
            logger.error("ONE OR MORE INVARIANTS FAILED — review metrics before demo.")
