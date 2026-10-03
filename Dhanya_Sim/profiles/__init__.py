"""Client profiles package for Fair Drop adversarial simulation.

Exports all 10 simulated persona classes and a centralized PROFILE_REGISTRY.
"""

from typing import Dict, Type

from .account_farm import AccountFarm
from .base_profile import BaseProfile
from .burst_bot import BurstBot
from .direct_api_bot import DirectAPIBot
from .fast_bot import FastBot
from .normal_human import NormalHuman
from .race_condition_attacker import RaceConditionAttacker
from .retry_bot import RetryBot
from .shared_network_user import SharedNetworkUser
from .slow_accessibility_user import SlowAccessibilityUser
from .token_replay_attacker import TokenReplayAttacker
from .honeypot_trigger_bot import HoneypotTriggerBot
from .honeypot_aware_bot import HoneypotAwareBot
from .single_ip_burst_bot import SingleIPBurstBot
from .distributed_botnet import DistributedBotnet
from .datacenter_bot import DatacenterBot

PROFILE_REGISTRY: Dict[str, Type[BaseProfile]] = {
    "normal_human": NormalHuman,
    "fast_bot": FastBot,
    "burst_bot": BurstBot,
    "retry_bot": RetryBot,
    "account_farm": AccountFarm,
    "direct_api_bot": DirectAPIBot,
    "token_replay_attacker": TokenReplayAttacker,
    "race_condition_attacker": RaceConditionAttacker,
    "shared_network_user": SharedNetworkUser,
    "slow_accessibility_user": SlowAccessibilityUser,
    "honeypot_trigger_bot": HoneypotTriggerBot,
    "honeypot_aware_bot": HoneypotAwareBot,
    "single_ip_burst_bot": SingleIPBurstBot,
    "distributed_botnet": DistributedBotnet,
    "datacenter_bot": DatacenterBot,
}

__all__ = [
    "BaseProfile",
    "NormalHuman",
    "FastBot",
    "BurstBot",
    "RetryBot",
    "AccountFarm",
    "DirectAPIBot",
    "TokenReplayAttacker",
    "RaceConditionAttacker",
    "SharedNetworkUser",
    "SlowAccessibilityUser",
    "HoneypotTriggerBot",
    "HoneypotAwareBot",
    "SingleIPBurstBot",
    "DistributedBotnet",
    "DatacenterBot",
    "PROFILE_REGISTRY",
]
