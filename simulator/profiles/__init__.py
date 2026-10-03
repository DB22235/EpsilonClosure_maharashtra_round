"""Fair Drop live simulator — client profiles package.

Exports all 8 adversarial and legitimate profile classes.
"""

from profiles.normal_human import NormalHuman
from profiles.fast_bot import FastBot
from profiles.burst_bot import BurstBot
from profiles.retry_bot import RetryBot
from profiles.direct_api_bot import DirectAPIBot
from profiles.token_replay import TokenReplayAttacker
from profiles.race_attacker import RaceAttacker
from profiles.shared_network import SharedNetworkUser

__all__ = [
    "NormalHuman",
    "FastBot",
    "BurstBot",
    "RetryBot",
    "DirectAPIBot",
    "TokenReplayAttacker",
    "RaceAttacker",
    "SharedNetworkUser",
]
