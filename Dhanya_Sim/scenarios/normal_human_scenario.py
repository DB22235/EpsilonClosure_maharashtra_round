"""Baseline normal-human registration scenario for Fair Drop.

Tests that the system handles a fully legitimate traffic population correctly:
all participants should be registered, deduplication should be transparent,
and no integrity violations should occur.
"""

from __future__ import annotations

import logging

from .base_scenario import BaseScenario, ScenarioConfig
from ..runner.engine import SimulationEngine
from ..profiles.normal_human import NormalHuman

logger = logging.getLogger(__name__)


class NormalHumanScenario(BaseScenario):
    """Scenario: 100% normal human participants, zero adversarial load.

    Validates:
    - All participants can register exactly once.
    - No rate-limit false positives for legitimate users.
    - Zero integrity violations (oversell / duplicate allocation / replay).
    - Lottery selection rate is proportional across all participants.
    """

    name = "normal_human_baseline"
    description = (
        "Sends 100% legitimate human traffic to validate baseline registration "
        "correctness, idempotency, and zero integrity violations."
    )

    def __init__(self, config: ScenarioConfig, num_participants: int = 200) -> None:
        """Initialise the scenario.

        Args:
            config: Scenario configuration.
            num_participants: Number of unique human participants to simulate.
        """
        super().__init__(config)
        self._num_participants = num_participants

    def setup(self) -> None:
        """Generate unique human participant identities."""
        self.identities = [
            self._make_identity(i, prefix="human")
            for i in range(self._num_participants)
        ]
        logger.info(
            "NormalHumanScenario setup: %d participants for campaign %s",
            len(self.identities),
            self.config.campaign_id,
        )

    async def run(self) -> None:
        """Execute the normal-human scenario and collect metrics."""
        engine_config = self._build_engine_config()
        async with SimulationEngine(config=engine_config) as engine:
            await engine.run_scenario(
                profile_class=NormalHuman,
                identities=self.identities,
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
        logger.info("NormalHumanScenario complete — %d records", summary.get("participation", {}).get("total_requests", 0))
