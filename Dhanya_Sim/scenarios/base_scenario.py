"""Base simulation scenario for Fair Drop adversarial testing.

Scenarios define the parameters, target endpoints, client populations, and
evaluation metrics for testing Fair Drop under specific load and threat models.

Core Scenarios in Fair Drop:
 1. Normal registration with no abuse (baseline legitimate traffic).
 2. High-volume duplicate requests from single identities (deduplication test).
 3. Distributed moderate-volume botnets (bot vs human allocation comparison).
 4. Retry after lost response (idempotency verification under network failure).
 5. Direct API access without frontend flow (server-side boundary enforcement).
 6. Admission-token replay attacks (permit signature and nonce validity).
 7. Challenge replay attacks (one-time challenge token expiration).
 8. Entitlement replay attacks (single-use winner entitlement consumption).
 9. Concurrent race condition on identical seat allocation (atomic inventory).
10. Hold expiration and standby promotion (seat recovery lifecycle).
11. Database/cache temporary failure injection (graceful degradation).
12. Shared-network multi-user clusters (false positive rate auditing).
13. Slow users competing with high-speed bots (fairness confirmation).
14. Full mixed population demo scenario (500 seats / 50,000 users).
15. Registration cutoff boundary testing (in-flight request cutoffs).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScenarioConfig:
    """Validated configuration for a single simulation scenario.

    Attributes:
        campaign_id: Target campaign identifier.
        base_url: Fair Drop API base URL.
        capacity: Seat capacity for this campaign (used in integrity assertions).
        concurrency: Max simultaneous HTTP workers.
        timeout: Per-request HTTP timeout in seconds.
        http2: Enable HTTP/2 on the transport client.
        ramp_seconds: Warm-up ramp duration before full concurrency.
        output_dir: Directory for JSON/CSV report artefacts.
        tags: Arbitrary labels attached to the report for filtering.
        extra: Scenario-specific free-form configuration dict.
    """

    campaign_id: str
    base_url: str = "http://localhost:8000"
    capacity: int = 500
    concurrency: int = 50
    timeout: float = 10.0
    http2: bool = True
    ramp_seconds: float = 0.0
    output_dir: str = "output"
    mock_mode: bool = False
    scenario_id: int = 0
    tags: List[str] = field(default_factory=list)
    client_profiles: List[Dict[str, Any]] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseScenario(ABC):
    """Abstract base class for simulation test scenarios.

    Represents a specific test configuration, including client populations,
    timing boundaries, and target invariants to evaluate.

    Subclasses must implement:
    - ``setup()``: Prepare identities, fixtures, and state before ``run()``.
    - ``run()``: Execute the scenario HTTP traffic and collect metrics.

    Typical usage::

        scenario = BurstBotScenario(config=ScenarioConfig(
            campaign_id="camp_001",
            base_url="http://localhost:8000",
            capacity=500,
            concurrency=100,
        ))
        scenario.setup()
        await scenario.run()
        scenario.report()
    """

    #: Human-readable name for this scenario (used in reports).
    name: str = "base_scenario"
    #: Short description of what this scenario tests.
    description: str = "Abstract base scenario."

    def __init__(self, config: ScenarioConfig) -> None:
        """Initialise the scenario with a validated configuration.

        Args:
            config: ScenarioConfig dataclass instance describing the run parameters.
        """
        self.config: ScenarioConfig = config
        self.identities: List[Dict[str, Any]] = []
        self._results: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def setup(self) -> None:
        """Prepare scenario fixtures, generate client identities, and initialise state.

        This method is called once before ``run()``. Implementations should
        populate ``self.identities`` with participant dicts and perform any
        required one-off setup (e.g. seeding random state, pre-fetching tokens).
        """

    @abstractmethod
    async def run(self) -> None:
        """Execute the scenario against the Fair Drop HTTP API.

        Implementations should instantiate a SimulationEngine with ``self.config``,
        run the appropriate profile populations, collect metrics, and store
        the summary in ``self._results``.
        """

    # ------------------------------------------------------------------
    # Helper utilities available to all subclasses
    # ------------------------------------------------------------------

    def _build_engine_config(self) -> Dict[str, Any]:
        """Build the engine config dict from this scenario's ScenarioConfig."""
        return {
            "base_url": self.config.base_url,
            "concurrency": self.config.concurrency,
            "timeout": self.config.timeout,
            "http2": self.config.http2,
            "capacity": self.config.capacity,
            "ramp_seconds": self.config.ramp_seconds,
            "mock_mode": self.config.mock_mode,
            "scenario_id": self.config.scenario_id,
        }

    def _make_identity(
        self,
        index: int,
        prefix: str = "user",
        email_domain: str = "example.com",
    ) -> Dict[str, Any]:
        """Generate a synthetic participant identity dict.

        Args:
            index: Numeric suffix to ensure uniqueness.
            prefix: Identifier prefix string.
            email_domain: Email domain for the generated address.

        Returns:
            Dictionary with ``participant_id``, ``account_id``, and ``email`` keys.
        """
        pid = f"{prefix}_{index:05d}"
        return {
            "participant_id": pid,
            "account_id": pid,
            "email": f"{pid}@{email_domain}",
        }

    def report(self) -> Optional[Dict[str, Any]]:
        """Return the scenario's results dictionary, or None if not yet run.

        Returns:
            Aggregated metrics summary, or None if ``run()`` has not completed.
        """
        return self._results
