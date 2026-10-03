"""Scenarios package for Fair Drop adversarial simulation.

Exports all scenario classes and provides SCENARIO_REGISTRY — a mapping from
scenario ID (int or str) and name to the corresponding scenario class and its
default YAML config path.
"""

from __future__ import annotations

from pathlib import Path

from .base_scenario import BaseScenario, ScenarioConfig
from .normal_human_scenario import NormalHumanScenario
from .burst_bot_scenario import BurstBotScenario
from .mixed_demo_scenario import MixedDemoScenario
from .adversarial_scenarios import (
    BurstDeduplicationScenario,
    RaceConditionScenario,
    ReplayAttackScenario,
    IdempotencyScenario,
    SharedIPFalsePositiveScenario,
    MixedAdversarialScenario,
)

_CONFIGS_DIR = Path(__file__).parent.parent / "configs"


def _cfg(filename: str) -> str:
    return str(_CONFIGS_DIR / filename)


# ---------------------------------------------------------------------------
# SCENARIO_REGISTRY
# Keys: integer ID (1-15) and string name alias.
# Each value is a dict with:
#   - "class"       : the scenario class to instantiate
#   - "config_path" : path to the default YAML config file
#   - "description" : one-line summary
# ---------------------------------------------------------------------------
SCENARIO_REGISTRY: dict = {
    1: {
        "class": NormalHumanScenario,
        "config_path": _cfg("01_normal_baseline.yaml"),
        "description": "Normal baseline — 1,000 humans, 500 seats, zero bots.",
        "name": "normal_baseline",
    },
    2: {
        "class": BurstDeduplicationScenario,
        "config_path": _cfg("02_burst_attack.yaml"),
        "description": "Burst deduplication — 50 bots × 100 requests per identity.",
        "name": "burst_attack",
    },
    3: {
        "class": BurstBotScenario,
        "config_path": _cfg("03_distributed_bots.yaml"),
        "description": "Distributed bots — 5,000 fast bots vs 1,000 humans.",
        "name": "distributed_bots",
    },
    4: {
        "class": IdempotencyScenario,
        "config_path": _cfg("04_retry_idempotency.yaml"),
        "description": "Retry idempotency — 200 retry bots, mutated-payload rejection.",
        "name": "retry_idempotency",
    },
    5: {
        "class": ReplayAttackScenario,
        "config_path": _cfg("05_direct_api_bypass.yaml"),
        "description": "Direct API bypass — 100 bots, no permits.",
        "name": "direct_api_bypass",
    },
    6: {
        "class": ReplayAttackScenario,
        "config_path": _cfg("06_token_replay.yaml"),
        "description": "Token replay — 50 attackers replaying admission permits.",
        "name": "token_replay",
    },
    7: {
        "class": ReplayAttackScenario,
        "config_path": _cfg("07_challenge_replay.yaml"),
        "description": "Challenge replay — 50 attackers reusing challenge tokens.",
        "name": "challenge_replay",
    },
    8: {
        "class": ReplayAttackScenario,
        "config_path": _cfg("08_entitlement_replay.yaml"),
        "description": "Entitlement replay — 50 attackers replaying winner tokens.",
        "name": "entitlement_replay",
    },
    9: {
        "class": RaceConditionScenario,
        "config_path": _cfg("09_race_condition_seat.yaml"),
        "description": "Race condition — 50 racers, 10 seats, zero ramp.",
        "name": "race_condition_seat",
    },
    10: {
        "class": NormalHumanScenario,
        "config_path": _cfg("10_hold_expiry_standby.yaml"),
        "description": "Hold expiry & standby — winners abandon holds.",
        "name": "hold_expiry_standby",
    },
    11: {
        "class": IdempotencyScenario,
        "config_path": _cfg("11_network_failure_recovery.yaml"),
        "description": "Network failure recovery — 20% drop rate, retry recovery.",
        "name": "network_failure_recovery",
    },
    12: {
        "class": SharedIPFalsePositiveScenario,
        "config_path": _cfg("12_shared_ip_network.yaml"),
        "description": "Shared IP — 500 users, 2 IPs, false positive rate < 5%.",
        "name": "shared_ip_network",
    },
    13: {
        "class": MixedAdversarialScenario,
        "config_path": _cfg("13_slow_vs_fast.yaml"),
        "description": "Slow vs fast — 200 accessibility users vs 500 fast bots.",
        "name": "slow_vs_fast",
    },
    14: {
        "class": BurstBotScenario,
        "config_path": _cfg("14_cutoff_boundary.yaml"),
        "description": "Cutoff boundary — requests within ±100ms of registration close.",
        "name": "cutoff_boundary",
    },
    15: {
        "class": MixedDemoScenario,
        "config_path": _cfg("15_flagship_mixed_50k.yaml"),
        "description": "Flagship mixed 50k — judge demo, all profiles.",
        "name": "flagship_mixed_50k",
    },
}

# Name-to-ID index for convenient lookup by string
SCENARIO_NAME_INDEX: dict[str, int] = {
    v["name"]: k for k, v in SCENARIO_REGISTRY.items()
}


def get_scenario(key: "int | str") -> dict:
    """Return registry entry for scenario by ID (int) or name (str).

    Args:
        key: Integer scenario ID (1-15) or string name alias.

    Returns:
        Registry dict with keys: class, config_path, description, name.

    Raises:
        KeyError: If the key does not match any registered scenario.
    """
    if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
        return SCENARIO_REGISTRY[int(key)]
    if isinstance(key, str):
        sid = SCENARIO_NAME_INDEX.get(key)
        if sid is None:
            raise KeyError(f"Unknown scenario name: '{key}'. "
                           f"Available: {list(SCENARIO_NAME_INDEX)}")
        return SCENARIO_REGISTRY[sid]
    raise KeyError(f"Invalid scenario key type: {type(key)}")


__all__ = [
    # Base
    "BaseScenario",
    "ScenarioConfig",
    # Concrete (simple)
    "NormalHumanScenario",
    "BurstBotScenario",
    "MixedDemoScenario",
    # Adversarial
    "BurstDeduplicationScenario",
    "RaceConditionScenario",
    "ReplayAttackScenario",
    "IdempotencyScenario",
    "SharedIPFalsePositiveScenario",
    "MixedAdversarialScenario",
    # Registry
    "SCENARIO_REGISTRY",
    "SCENARIO_NAME_INDEX",
    "get_scenario",
]
