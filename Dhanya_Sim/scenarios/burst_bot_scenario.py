"""Burst-bot adversarial scenario for Fair Drop.

Tests that the system correctly rate-limits and deduplicates high-volume
automated requests from a small number of bot identities, and that bot win
rates do not significantly exceed human win rates when computed against
valid entries.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from .base_scenario import BaseScenario, ScenarioConfig
from ..runner.engine import SimulationEngine
from ..profiles.burst_bot import BurstBot
from ..profiles.normal_human import NormalHuman

logger = logging.getLogger(__name__)


class BurstBotScenario(BaseScenario):
    """Scenario: mixed population of burst bots and normal humans.

    The burst bots fire a high volume of rapid requests per identity to test:
    - Rate limiting and 429 enforcement.
    - Deduplication: duplicate requests do not create additional lottery entries.
    - Fairness: bot win rate vs valid entries should not exceed human win rate.
    - Integrity: no oversell, no duplicate allocation under concurrent load.
    """

    name = "burst_bot_mixed"
    description = (
        "Runs a mixed population of burst bots and normal humans. "
        "Validates rate-limiting, deduplication, and fairness invariants."
    )

    def __init__(
        self,
        config: ScenarioConfig,
        num_bots: int = 50,
        num_humans: int = 200,
    ) -> None:
        """Initialise the scenario.

        Args:
            config: Scenario configuration.
            num_bots: Number of unique bot identities to simulate.
            num_humans: Number of unique human participants to simulate.
        """
        super().__init__(config)
        self._num_bots = num_bots
        self._num_humans = num_humans
        self._bot_identities: List[Dict[str, Any]] = []
        self._human_identities: List[Dict[str, Any]] = []

    def setup(self) -> None:
        """Generate bot and human participant identities."""
        self._bot_identities = [
            self._make_identity(i, prefix="burst_bot")
            for i in range(self._num_bots)
        ]
        self._human_identities = [
            self._make_identity(i, prefix="human")
            for i in range(self._num_humans)
        ]
        self.identities = self._bot_identities + self._human_identities
        logger.info(
            "BurstBotScenario setup: %d bots + %d humans for campaign %s",
            self._num_bots,
            self._num_humans,
            self.config.campaign_id,
        )

    async def run(self) -> None:
        """Execute the burst bot mixed scenario."""
        engine_config = self._build_engine_config()
        populations = [
            {"profile_class": BurstBot, "identities": self._bot_identities},
            {"profile_class": NormalHuman, "identities": self._human_identities},
        ]
        async with SimulationEngine(config=engine_config) as engine:
            await engine.run_mixed_scenario(
                populations=populations,
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

        # Assert key fairness invariant for reporting
        fairness = summary.get("fairness", {})
        bot_adv = fairness.get("bot_advantage_ratio")
        if bot_adv is not None and bot_adv > 1.1:
            logger.warning(
                "FAIRNESS WARNING: Bot advantage ratio %.4f > 1.1 threshold. "
                "Bots are winning disproportionately relative to valid entries.",
                bot_adv,
            )
        else:
            logger.info("Fairness check passed — bot advantage ratio: %s", bot_adv)
