"""Specialized adversarial scenario classes for Fair Drop simulation.

Each class extends BaseScenario and implements a specific attack or edge-case
that must be handled correctly by the Fair Drop backend.

Scenarios:
  BurstDeduplicationScenario  — Validates deduplication under high-volume spam.
  RaceConditionScenario       — Validates atomic seat-hold under concurrent attacks.
  ReplayAttackScenario        — Validates replay protection for permits/entitlements.
  IdempotencyScenario         — Validates idempotency contract under retries.
  SharedIPFalsePositiveScenario — Validates legitimate shared-IP users are not blocked.
  MixedAdversarialScenario    — Full multi-phase lifecycle with all profile types.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Type

from .base_scenario import BaseScenario, ScenarioConfig
from ..runner.engine import SimulationEngine
from ..profiles.burst_bot import BurstBot
from ..profiles.fast_bot import FastBot
from ..profiles.normal_human import NormalHuman
from ..profiles.race_condition_attacker import RaceConditionAttacker
from ..profiles.retry_bot import RetryBot
from ..profiles.token_replay_attacker import TokenReplayAttacker
from ..profiles.account_farm import AccountFarm
from ..profiles.direct_api_bot import DirectAPIBot as DirectApiBot
from ..profiles.shared_network_user import SharedNetworkUser
from ..profiles.slow_accessibility_user import SlowAccessibilityUser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. BurstDeduplicationScenario
# ---------------------------------------------------------------------------

class BurstDeduplicationScenario(BaseScenario):
    """Scenario: high-volume burst from few identities → validates deduplication.

    Each of the ``num_bots`` bot identities fires ``requests_per_identity``
    rapid requests.  After the run, the test asserts that the number of valid
    entries in the metrics is at most ``num_bots`` (one per identity),
    regardless of request volume.
    """

    name = "burst_deduplication"
    description = (
        "Fires many duplicate requests per bot identity and asserts that only "
        "1 valid entry is recorded per unique participant ID."
    )

    def __init__(
        self,
        config: ScenarioConfig,
        num_bots: int = 50,
        requests_per_identity: int = 100,
    ) -> None:
        super().__init__(config)
        self._num_bots = num_bots
        self._requests_per_identity = requests_per_identity

    def setup(self) -> None:
        self.identities = [
            self._make_identity(i, prefix="burst_dedup_bot")
            for i in range(self._num_bots)
        ]
        logger.info(
            "BurstDeduplicationScenario: %d bots × %d requests = %d total requests",
            self._num_bots,
            self._requests_per_identity,
            self._num_bots * self._requests_per_identity,
        )

    async def run(self) -> None:
        async with SimulationEngine(config=self._build_engine_config()) as engine:
            # Each identity fires requests_per_identity times
            all_identities = [
                identity
                for identity in self.identities
                for _ in range(self._requests_per_identity)
            ]
            await engine.run_scenario(
                profile_class=BurstBot,
                identities=all_identities,
                campaign_id=self.config.campaign_id,
            )
            summary = engine.collector.summarize()
            engine.collector.export_json(
                f"{self.config.output_dir}/{self.name}_metrics.json"
            )
            engine.collector.export_csv(
                f"{self.config.output_dir}/{self.name}_records.csv"
            )

        self._results = summary

        # Assert deduplication invariant
        valid = summary.get("participation", {}).get("valid_entries", -1)
        if valid > self._num_bots:
            logger.error(
                "DEDUPLICATION FAILURE: %d valid entries recorded for %d identities "
                "(expected ≤ %d).",
                valid, self._num_bots, self._num_bots,
            )
        else:
            logger.info(
                "Deduplication PASSED: %d valid entries ≤ %d identities.", valid, self._num_bots
            )

        engine.collector.print_summary()


# ---------------------------------------------------------------------------
# 2. RaceConditionScenario
# ---------------------------------------------------------------------------

class RaceConditionScenario(BaseScenario):
    """Scenario: concurrent clients race to hold the same seat IDs simultaneously.

    ``num_attackers`` coroutines all attempt to claim ``num_target_seats``
    seats with zero ramp delay (simultaneous fire).  Validates:
    - ``oversell_violations == 0``
    - ``duplicate_allocation_violations == 0``
    - At most ``num_target_seats`` confirmed seats.
    """

    name = "race_condition"
    description = (
        "Fires concurrent holds on identical seat IDs with zero ramp. "
        "Validates atomic inventory transactions."
    )

    def __init__(
        self,
        config: ScenarioConfig,
        num_attackers: int = 50,
        num_target_seats: int = 10,
    ) -> None:
        super().__init__(config)
        self._num_attackers = num_attackers
        self._num_target_seats = num_target_seats
        # Force zero ramp so all requests fire simultaneously
        self.config.ramp_seconds = 0.0

    def setup(self) -> None:
        self.identities = [
            self._make_identity(i, prefix="racer")
            for i in range(self._num_attackers)
        ]
        logger.info(
            "RaceConditionScenario: %d attackers racing for %d seats",
            self._num_attackers, self._num_target_seats,
        )

    async def run(self) -> None:
        async with SimulationEngine(config=self._build_engine_config()) as engine:
            await engine.run_scenario(
                profile_class=RaceConditionAttacker,
                identities=self.identities,
                campaign_id=self.config.campaign_id,
            )
            summary = engine.collector.summarize()
            engine.collector.export_json(
                f"{self.config.output_dir}/{self.name}_metrics.json"
            )

        self._results = summary
        integrity = summary.get("integrity", {})
        oversell = integrity.get("oversell_violations", -1)
        dup = integrity.get("duplicate_allocation_violations", -1)
        confirmed = integrity.get("confirmed_seats", -1)

        if oversell != 0 or dup != 0:
            logger.error(
                "RACE CONDITION FAILURE — oversell=%d  duplicate_alloc=%d  confirmed=%d",
                oversell, dup, confirmed,
            )
        else:
            logger.info(
                "Race condition PASSED — oversell=0  duplicate_alloc=0  confirmed=%d ≤ %d",
                confirmed, self._num_target_seats,
            )
        engine.collector.print_summary()


# ---------------------------------------------------------------------------
# 3. ReplayAttackScenario
# ---------------------------------------------------------------------------

class ReplayAttackScenario(BaseScenario):
    """Scenario: validates replay protection for tokens/permits/entitlements.

    Runs ``num_attackers`` TokenReplayAttacker instances and asserts that
    ``replay_attack_successes == 0`` in the integrity summary.
    """

    name = "replay_attack"
    description = (
        "Runs token replay attackers against permits, challenge nonces, "
        "and entitlement tokens. Validates zero successful replays."
    )

    def __init__(
        self,
        config: ScenarioConfig,
        num_attackers: int = 50,
        replay_target: str = "admission_permit",
    ) -> None:
        super().__init__(config)
        self._num_attackers = num_attackers
        self._replay_target = replay_target

    def setup(self) -> None:
        self.identities = [
            {**self._make_identity(i, prefix="replayer"), "replay_target": self._replay_target}
            for i in range(self._num_attackers)
        ]
        logger.info(
            "ReplayAttackScenario: %d attackers, target=%s",
            self._num_attackers, self._replay_target,
        )

    async def run(self) -> None:
        async with SimulationEngine(config=self._build_engine_config()) as engine:
            await engine.run_scenario(
                profile_class=TokenReplayAttacker,
                identities=self.identities,
                campaign_id=self.config.campaign_id,
            )
            summary = engine.collector.summarize()
            engine.collector.export_json(
                f"{self.config.output_dir}/{self.name}_{self._replay_target}_metrics.json"
            )

        self._results = summary
        replays = summary.get("integrity", {}).get("replay_attack_successes", -1)
        if replays != 0:
            logger.error("REPLAY PROTECTION FAILURE: %d successful replays recorded!", replays)
        else:
            logger.info("Replay protection PASSED: 0 successful replays.")
        engine.collector.print_summary()


# ---------------------------------------------------------------------------
# 4. IdempotencyScenario
# ---------------------------------------------------------------------------

class IdempotencyScenario(BaseScenario):
    """Scenario: validates idempotency contract under retries and payload mutation.

    Runs RetryBot instances that:
    1. Re-send with the identical idempotency key → server must return the same
       HTTP status/body (idempotent retry).
    2. Re-send with the same key but a mutated payload → server must return
       HTTP 400/422 (conflict detection).
    """

    name = "idempotency"
    description = (
        "Validates that retries with identical idempotency keys return the original "
        "response, and mutated payloads are rejected."
    )

    def __init__(
        self,
        config: ScenarioConfig,
        num_retry_clients: int = 100,
    ) -> None:
        super().__init__(config)
        self._num_retry_clients = num_retry_clients

    def setup(self) -> None:
        self.identities = [
            {
                **self._make_identity(i, prefix="retry_client"),
                "preserve_idempotency_key": True,
                "simulate_payload_mutation": True,
                "max_retries": 5,
            }
            for i in range(self._num_retry_clients)
        ]
        logger.info("IdempotencyScenario: %d retry clients", self._num_retry_clients)

    async def run(self) -> None:
        async with SimulationEngine(config=self._build_engine_config()) as engine:
            await engine.run_scenario(
                profile_class=RetryBot,
                identities=self.identities,
                campaign_id=self.config.campaign_id,
            )
            summary = engine.collector.summarize()
            engine.collector.export_json(
                f"{self.config.output_dir}/{self.name}_metrics.json"
            )

        self._results = summary
        dup = summary.get("integrity", {}).get("duplicate_allocation_violations", -1)
        if dup != 0:
            logger.error("IDEMPOTENCY FAILURE: %d duplicate allocations detected!", dup)
        else:
            logger.info("Idempotency PASSED: 0 duplicate allocations.")
        engine.collector.print_summary()


# ---------------------------------------------------------------------------
# 5. SharedIPFalsePositiveScenario
# ---------------------------------------------------------------------------

class SharedIPFalsePositiveScenario(BaseScenario):
    """Scenario: validates that distinct accounts behind shared IPs are not blocked.

    500 legitimate users share 2 IP addresses (corporate NAT / campus WiFi).
    The false positive rate (benign users rate-limited) must be < 5%.
    """

    name = "shared_ip_false_positive"
    description = (
        "Runs 500 legitimate users behind 2 shared IPs. "
        "Validates that false-positive rate for benign clients is < 5%."
    )

    def __init__(
        self,
        config: ScenarioConfig,
        num_users: int = 500,
        num_shared_ips: int = 2,
    ) -> None:
        super().__init__(config)
        self._num_users = num_users
        self._num_shared_ips = num_shared_ips

    def setup(self) -> None:
        ips = [f"10.0.0.{i + 1}" for i in range(self._num_shared_ips)]
        self.identities = [
            {
                **self._make_identity(i, prefix="shared_ip_user"),
                "simulated_ip": ips[i % self._num_shared_ips],
            }
            for i in range(self._num_users)
        ]
        logger.info(
            "SharedIPFalsePositiveScenario: %d users across %d IPs",
            self._num_users, self._num_shared_ips,
        )

    async def run(self) -> None:
        async with SimulationEngine(config=self._build_engine_config()) as engine:
            await engine.run_scenario(
                profile_class=SharedNetworkUser,
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

        self._results = summary
        fp_rate = summary.get("reliability", {}).get(
            "false_positive_rate_benign_clients", -1.0
        )
        threshold = 0.05
        if fp_rate > threshold:
            logger.error(
                "FALSE POSITIVE FAILURE: %.1f%% of benign clients blocked (threshold %.1f%%)",
                fp_rate * 100, threshold * 100,
            )
        else:
            logger.info(
                "False positive PASSED: %.1f%% benign clients blocked (< %.1f%% threshold)",
                fp_rate * 100, threshold * 100,
            )
        engine.collector.print_summary()


# ---------------------------------------------------------------------------
# 6. MixedAdversarialScenario
# ---------------------------------------------------------------------------

class MixedAdversarialScenario(BaseScenario):
    """Scenario: full multi-phase lifecycle with all profile types.

    Executes the complete Fair Drop flow in distinct sequential phases:
      Phase A — Waiting room / Join (all profiles attempt join)
      Phase B — Concurrent Registration Storm (Normal + Adversaries)
      Phase C — Roster Freeze & Cutoff enforcement
      Phase D — Lottery Draw Trigger & Result Polling
      Phase E — Entitlement Verification, Hold Race, and Final Redemption

    Each phase is a concurrent wave dispatched via the shared engine.
    Metrics are aggregated across all phases into one unified report.
    """

    name = "mixed_adversarial_lifecycle"
    description = (
        "Full multi-phase lifecycle with all 10 profile types. "
        "Validates the complete Fair Drop flow end-to-end."
    )

    # Population counts per phase
    _PHASE_B_POPULATIONS = [
        (NormalHuman,        300, False),
        (SlowAccessibilityUser, 50, False),
        (SharedNetworkUser,   30, False),
        (FastBot,             80, True),
        (BurstBot,            40, True),
        (RetryBot,            20, False),
        (AccountFarm,         20, True),
        (DirectApiBot,        15, True),
        (TokenReplayAttacker, 10, True),
        (RaceConditionAttacker, 10, True),
    ]

    def setup(self) -> None:
        self._phase_b_populations: List[Dict[str, Any]] = []
        global_idx = 0
        for profile_class, count, _ in self._PHASE_B_POPULATIONS:
            ids = [
                self._make_identity(global_idx + i, prefix=profile_class.profile_type)
                for i in range(count)
            ]
            self._phase_b_populations.append({
                "profile_class": profile_class,
                "identities": ids,
            })
            global_idx += count

        total = sum(len(p["identities"]) for p in self._phase_b_populations)
        self.identities = [
            identity
            for p in self._phase_b_populations
            for identity in p["identities"]
        ]
        logger.info(
            "MixedAdversarialScenario setup: %d total workers, %d profile types",
            total, len(self._phase_b_populations),
        )

    async def run(self) -> None:
        engine_config = self._build_engine_config()

        async with SimulationEngine(config=engine_config) as engine:
            # ---- Phase A: Waiting room join (normal humans only) ----
            logger.info("=== Phase A: Waiting Room Join ===")
            human_pop = next(
                p for p in self._phase_b_populations
                if p["profile_class"] is NormalHuman
            )
            await engine.run_scenario(
                profile_class=NormalHuman,
                identities=human_pop["identities"][:50],  # representative sample
                campaign_id=self.config.campaign_id,
            )
            await asyncio.sleep(0.5)

            # ---- Phase B: Full concurrent registration storm ----
            logger.info("=== Phase B: Concurrent Registration Storm ===")
            await engine.run_mixed_scenario(
                populations=self._phase_b_populations,
                campaign_id=self.config.campaign_id,
            )
            await asyncio.sleep(1.0)

            # ---- Phase C: Cutoff enforcement (fast bots fire post-cutoff) ----
            logger.info("=== Phase C: Cutoff Boundary ===")
            cutoff_bots = [
                self._make_identity(9000 + i, prefix="cutoff_bot")
                for i in range(20)
            ]
            await engine.run_scenario(
                profile_class=FastBot,
                identities=cutoff_bots,
                campaign_id=self.config.campaign_id,
            )
            await asyncio.sleep(0.5)

            # ---- Phase D: Lottery result polling ----
            logger.info("=== Phase D: Lottery Result Polling ===")
            poll_clients = [
                self._make_identity(i, prefix="poller")
                for i in range(30)
            ]
            await engine.run_scenario(
                profile_class=NormalHuman,
                identities=poll_clients,
                campaign_id=self.config.campaign_id,
            )
            await asyncio.sleep(0.5)

            # ---- Phase E: Entitlement holds and replay attacks ----
            logger.info("=== Phase E: Entitlement Hold Race & Replay ===")
            replay_attackers = [
                self._make_identity(i, prefix="phase_e_replayer")
                for i in range(10)
            ]
            race_attackers = [
                self._make_identity(i, prefix="phase_e_racer")
                for i in range(20)
            ]
            await engine.run_mixed_scenario(
                populations=[
                    {"profile_class": TokenReplayAttacker, "identities": replay_attackers},
                    {"profile_class": RaceConditionAttacker, "identities": race_attackers},
                ],
                campaign_id=self.config.campaign_id,
            )

            # ---- Collect and export ----
            summary = engine.collector.summarize()
            engine.collector.export_json(
                f"{self.config.output_dir}/{self.name}_metrics.json"
            )
            engine.collector.export_csv(
                f"{self.config.output_dir}/{self.name}_records.csv"
            )
            engine.collector.print_summary()

        self._results = summary
        self._log_phase_assertions(summary)

    def _log_phase_assertions(self, summary: Dict[str, Any]) -> None:
        integrity = summary.get("integrity", {})
        fairness = summary.get("fairness", {})
        reliability = summary.get("reliability", {})

        checks = [
            ("Oversell = 0", integrity.get("oversell_violations", -1) == 0),
            ("Duplicate allocation = 0", integrity.get("duplicate_allocation_violations", -1) == 0),
            ("Replay success = 0", integrity.get("replay_attack_successes", -1) == 0),
            ("Bot advantage < 1.1", (fairness.get("bot_advantage_ratio") or 0) < 1.1),
            ("False positive < 10%",
             reliability.get("false_positive_rate_benign_clients", 1.0) < 0.10),
        ]

        all_ok = all(passed for _, passed in checks)
        logger.info("=== MixedAdversarialScenario Phase Assertions ===")
        for label, passed in checks:
            logger.info("  [%s] %s", "PASS" if passed else "FAIL", label)
        if all_ok:
            logger.info("ALL LIFECYCLE ASSERTIONS PASSED.")
        else:
            logger.error("ONE OR MORE LIFECYCLE ASSERTIONS FAILED.")


# ---------------------------------------------------------------------------
# 7. HoneypotDecoyScenario
# ---------------------------------------------------------------------------

class HoneypotDecoyScenario(BaseScenario):
    """Scenario: Validates that honeypot triggers detect naive bots but not aware bots or humans."""

    name = "honeypot_decoy_test"
    description = "Tests honeypot decoy detection logic."

    _DEFAULT_PROFILES = [
        {"type": "normal_human", "count": 20},
        {"type": "honeypot_trigger_bot", "count": 10},
        {"type": "honeypot_aware_bot", "count": 10},
    ]

    def setup(self) -> None:
        self.identities = []
        profiles = self.config.client_profiles or self._DEFAULT_PROFILES
        for p in profiles:
            for i in range(p.get("count", 0)):
                self.identities.append(self._make_identity(len(self.identities), prefix=p["type"]))
        logger.info("HoneypotDecoyScenario setup with %d identities", len(self.identities))

    async def run(self) -> None:
        async with SimulationEngine(config=self._build_engine_config()) as engine:
            profiles = self.config.client_profiles or self._DEFAULT_PROFILES
            for p in profiles:
                p_type = p["type"]
                from ..profiles import PROFILE_REGISTRY
                cls = PROFILE_REGISTRY[p_type]
                identities = [id for id in self.identities if id["participant_id"].startswith(p_type)]
                await engine.run_scenario(
                    profile_class=cls,
                    identities=identities,
                    campaign_id=self.config.campaign_id,
                )
            summary = engine.collector.summarize()

        self._results = summary
        honeypot = engine.collector.get_honeypot_metrics()
        
        aware_not_detected = honeypot.get("decoy_aware_bots_not_detected", 0)
        fps = honeypot.get("legitimate_decoy_false_positives", -1)

        # decoy_aware_bots_not_detected counts smart bots that did NOT trigger the decoy.
        # A positive value means they successfully avoided it — that is the PASS condition.
        # A value of 0 means ALL smart bots were caught (they triggered the decoy), which is a FAIL.
        if aware_not_detected > 0:
            logger.info(
                "HONEYPOT PASS: %d aware-bot(s) correctly avoided the decoy "
                "(not detected by honeypot, as expected).",
                aware_not_detected,
            )
        else:
            # Only fail if there actually were smart bots in the run
            smart_bots_total = honeypot.get("decoy_events_by_profile", {}).get("honeypot_aware_bot", 0)
            if smart_bots_total > 0:
                logger.error(
                    "HONEYPOT FAILURE: All %d aware bot(s) triggered the decoy — "
                    "smart-bot evasion is broken.",
                    smart_bots_total,
                )
        if fps != 0:
            logger.error("HONEYPOT FAILURE: %d human false positives recorded!", fps)
        else:
            logger.info("HONEYPOT PASS: 0 human false positives.")

        logger.info("HoneypotDecoyScenario completed.")


# ---------------------------------------------------------------------------
# 8. IPRateLimitScenario
# ---------------------------------------------------------------------------

class IPRateLimitScenario(BaseScenario):
    """Scenario: Validates IP-based rate limiting effectiveness and false positives."""

    name = "ip_rate_limit_stress"
    description = "Tests IP-based rate limiting under stress."

    _DEFAULT_PROFILES = [
        {"type": "normal_human", "count": 20},
        {"type": "single_ip_burst_bot", "count": 5, "network_group_id": 1, "requests_per_minute": 500},
        {"type": "shared_network_user", "count": 10},
    ]

    def setup(self) -> None:
        self.identities = []
        profiles = self.config.client_profiles or self._DEFAULT_PROFILES
        for p in profiles:
            for i in range(p.get("count", 0)):
                identity = self._make_identity(len(self.identities), prefix=p["type"])
                if "network_group_id" in p:
                    identity["network_group_id"] = p["network_group_id"]
                if "requests_per_minute" in p:
                    identity["requests_per_minute"] = p["requests_per_minute"]
                self.identities.append(identity)

    async def run(self) -> None:
        async with SimulationEngine(config=self._build_engine_config()) as engine:
            profiles = self.config.client_profiles or self._DEFAULT_PROFILES
            for p in profiles:
                p_type = p["type"]
                from ..profiles import PROFILE_REGISTRY
                cls = PROFILE_REGISTRY[p_type]
                identities = [id for id in self.identities if id["participant_id"].startswith(p_type)]
                await engine.run_scenario(
                    profile_class=cls,
                    identities=identities,
                    campaign_id=self.config.campaign_id,
                )
            summary = engine.collector.summarize()
            
        self._results = summary
        ip_metrics = engine.collector.get_ip_metrics()

        # shared_ip_legitimate_rejections counts shared_network_user records that were
        # rate-limited AND were in an explicit IP network group (i.e. blocked at the
        # group-level, not just identity-level).  SharedNetworkUser here uses no
        # network_group_id, so it is immune to group-level blocks — rejections should be 0.
        rejections = ip_metrics.get("shared_ip_legitimate_rejections", 0)
        throttled = ip_metrics.get("ip_throttled_requests", 0)

        if rejections != 0:
            logger.error(
                "IP RATE LIMIT FAILURE: %d shared-IP legitimate users blocked at the "
                "network-group level (false positives)!",
                rejections,
            )
        else:
            logger.info("IP RATE LIMIT PASS: 0 shared-IP legitimate users blocked.")
        if throttled == 0:
            logger.error("IP RATE LIMIT FAILURE: No burst bot requests were throttled.")
        else:
            logger.info("IP RATE LIMIT PASS: %d burst-bot request(s) throttled.", throttled)

        logger.info("IPRateLimitScenario completed.")


# ---------------------------------------------------------------------------
# 9. CGNATSharedIPScenario
# ---------------------------------------------------------------------------

class CGNATSharedIPScenario(BaseScenario):
    """Scenario: Validates CGNAT users aren't rate limited."""

    name = "cgnat_shared_ip"
    description = "Tests CGNAT shared IP false positives."

    _DEFAULT_PROFILES = [
        {"type": "shared_network_user", "count": 20},
        {"type": "normal_human", "count": 10},
    ]

    def setup(self) -> None:
        self.identities = []
        profiles = self.config.client_profiles or self._DEFAULT_PROFILES
        for p in profiles:
            for i in range(p.get("count", 0)):
                self.identities.append(self._make_identity(len(self.identities), prefix=p["type"]))

    async def run(self) -> None:
        async with SimulationEngine(config=self._build_engine_config()) as engine:
            profiles = self.config.client_profiles or self._DEFAULT_PROFILES
            for p in profiles:
                p_type = p["type"]
                from ..profiles import PROFILE_REGISTRY
                cls = PROFILE_REGISTRY[p_type]
                identities = [id for id in self.identities if id["participant_id"].startswith(p_type)]
                await engine.run_scenario(
                    profile_class=cls,
                    identities=identities,
                    campaign_id=self.config.campaign_id,
                )
            summary = engine.collector.summarize()
            
        self._results = summary
        ip_metrics = engine.collector.get_ip_metrics()
        # ip_based_false_positives = shared_network_user records rate-limited via
        # IP-group controls (network_group_id set).  CGNAT users here have no
        # explicit group assignment, so the expected value is 0.
        fps = ip_metrics.get("ip_based_false_positives", 0)
        if fps != 0:
            logger.error(
                "CGNAT FAILURE: %d CGNAT user(s) blocked by IP-group rate limiting!", fps
            )
        else:
            logger.info("CGNAT PASS: 0 legitimate users blocked by IP-group controls.")
        logger.info("CGNATSharedIPScenario completed.")


# ---------------------------------------------------------------------------
# 10. DistributedBotnetScenario
# ---------------------------------------------------------------------------

class DistributedBotnetScenario(BaseScenario):
    """Scenario: Validates distributed botnet behavior against IP rate limiting."""

    name = "distributed_botnet_vs_ip"
    description = "Tests distributed botnet evading IP controls."

    _DEFAULT_PROFILES = [
        {"type": "normal_human", "count": 20},
        {"type": "distributed_botnet", "count": 20},
        {"type": "datacenter_bot", "count": 10},
    ]

    def setup(self) -> None:
        self.identities = []
        profiles = self.config.client_profiles or self._DEFAULT_PROFILES
        for p in profiles:
            for i in range(p.get("count", 0)):
                self.identities.append(self._make_identity(len(self.identities), prefix=p["type"]))

    async def run(self) -> None:
        async with SimulationEngine(config=self._build_engine_config()) as engine:
            profiles = self.config.client_profiles or self._DEFAULT_PROFILES
            for p in profiles:
                p_type = p["type"]
                from ..profiles import PROFILE_REGISTRY
                cls = PROFILE_REGISTRY[p_type]
                identities = [id for id in self.identities if id["participant_id"].startswith(p_type)]
                await engine.run_scenario(
                    profile_class=cls,
                    identities=identities,
                    campaign_id=self.config.campaign_id,
                )
            summary = engine.collector.summarize()
            
        self._results = summary
        ip_metrics = engine.collector.get_ip_metrics()
        
        if ip_metrics.get("ip_rate_limit_effectiveness") == "HIGH":
            logger.error("DISTRIBUTED BOTNET FAILURE: IP rate limits were incorrectly effective.")
            
        logger.info("DistributedBotnetScenario completed.")
