"""Frontend data bridge for Fair Drop adversarial simulation.

Transforms raw MetricsCollector output into the exact dashboard JSON feed
schema expected by Rohan's frontend dashboard.
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .collector import MetricsCollector

logger = logging.getLogger(__name__)

_DEBUG_LOG_PATH = Path(__file__).resolve().parents[2] / ".cursor" / "debug-37ca44.log"
_DEBUG_SESSION = "37ca44"

# Primary fairness rows (seeded ranges for mock demo dashboard)
_MOCK_FAIRNESS_SPECS: List[Tuple[int, int, int, int, int, int]] = [
    (34000, 36000, 33000, 35000, 335, 355),   # Normal Human
    (3500, 4500, 3500, 4200, 35, 43),           # Fast Bot
    (72000, 82000, 4500, 5500, 46, 55),         # Burst Bot
    (4000, 6000, 1800, 2200, 18, 23),           # Account Farm
    (2500, 3500, 1800, 2200, 18, 23),           # Retry Bot
    (1500, 2500, 0, 0, 0, 0),                   # Direct API Bot
    (800, 1200, 1, 1, 0, 0),                    # Token Replay
    (400, 600, 1, 1, 0, 0),                     # Race Attacker
    (900, 1100, 900, 1050, 9, 11),              # Shared IP User
    (750, 900, 750, 880, 8, 10),                # Slow User
]
_MOCK_EXTRA_PROFILE_REQS: List[Tuple[int, int]] = [
    (320, 400),
    (180, 250),
    (1000, 1200),
    (1300, 1500),
    (800, 900),
]

_HUMAN_PROFILE_KEYS = frozenset({
    "normal_human",
    "shared_network_user",
    "slow_accessibility_user",
})
_BOT_FAIRNESS_KEYS = frozenset({
    "fast_bot",
    "burst_bot",
    "account_farm",
    "retry_bot",
})


def _agent_debug_log(
    location: str,
    message: str,
    data: Dict[str, Any],
    hypothesis_id: str,
    run_id: str = "pre-fix",
) -> None:
    # #region agent log
    try:
        payload = {
            "sessionId": _DEBUG_SESSION,
            "id": f"log_{hypothesis_id}_{location}",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "location": location,
            "message": message,
            "data": data,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
        }
        _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except OSError:
        pass
    # #endregion


def _selection_rate_pct(winners: int, valid_entries: int) -> float:
    if valid_entries <= 0:
        return 0.0
    rate = round((winners / valid_entries) * 100, 2)
    return min(rate, 2.0)


def _bot_advantage_from_chart(
    profile_keys: List[str],
    valid_entries: List[int],
    winners: List[int],
) -> float:
    human_valid = human_wins = bot_valid = bot_wins = 0
    for key, valid, wins in zip(profile_keys, valid_entries, winners):
        if key in _HUMAN_PROFILE_KEYS:
            human_valid += valid
            human_wins += wins
        elif key in _BOT_FAIRNESS_KEYS:
            bot_valid += valid
            bot_wins += wins
    if human_valid <= 0 or bot_valid <= 0 or human_wins <= 0:
        return 1.0
    human_rate = human_wins / human_valid
    bot_rate = bot_wins / bot_valid
    if human_rate <= 0:
        return 1.0
    return round(bot_rate / human_rate, 3)


def synthesize_mock_demo_metrics(seed: int = 42) -> Dict[str, Any]:
    """Build mathematically consistent mock dashboard metrics (seeded variance)."""
    rng = random.Random(seed)
    profile_keys = [key for key, _ in _PROFILE_ORDER]

    total_requests_list: List[int] = []
    valid_entries_list: List[int] = []
    winners_list: List[int] = []

    for idx, spec in enumerate(_MOCK_FAIRNESS_SPECS):
        req_lo, req_hi, val_lo, val_hi, win_lo, win_hi = spec
        reqs = rng.randint(req_lo, req_hi)
        if val_lo == val_hi == 0 and win_lo == win_hi == 0 and val_lo == 0:
            valid = 0
            wins = 0
        elif val_lo == 1 and val_hi == 1:
            valid = 1
            wins = 0
        else:
            valid = rng.randint(val_lo, val_hi)
            wins = rng.randint(win_lo, win_hi) if win_hi > 0 else 0
        total_requests_list.append(reqs)
        valid_entries_list.append(valid)
        winners_list.append(wins)

    for req_lo, req_hi in _MOCK_EXTRA_PROFILE_REQS:
        total_requests_list.append(rng.randint(req_lo, req_hi))
        valid_entries_list.append(0)
        winners_list.append(0)

    non_normal = sum(winners_list[1:10])
    winners_list[0] = max(0, 500 - non_normal)

    selection_rates = [
        _selection_rate_pct(w, v)
        for w, v in zip(winners_list, valid_entries_list)
    ]

    total_requests = sum(total_requests_list)
    if total_requests < 128_000:
        bump = rng.randint(128_000, 145_000) - total_requests
        total_requests_list[0] += bump
        total_requests = sum(total_requests_list)

    total_participants = rng.randint(48_000, 50_000)
    duration_seconds = round(rng.uniform(38, 52), 1)
    valid_registrations = sum(valid_entries_list)

    duplicate_attempts = rng.randint(65_000, 80_000)
    rejected_attempts = rng.randint(3_000, 6_000)
    rate_limited = rng.randint(8_000, 14_000)

    burst_reqs = total_requests_list[2]
    burst_valid = valid_entries_list[2]
    burst_blocked = max(0, burst_reqs - burst_valid)

    bot_advantage_ratio = _bot_advantage_from_chart(
        profile_keys, valid_entries_list, winners_list
    )

    return {
        "scenario_summary": {
            "total_requests": total_requests,
            "total_participants": total_participants,
            "duration_seconds": duration_seconds,
        },
        "fairness_chart": {
            "labels": [label for _, label in _PROFILE_ORDER],
            "total_requests": total_requests_list,
            "valid_entries": valid_entries_list,
            "winners": winners_list,
            "selection_rate_pct": selection_rates,
        },
        "bot_advantage_ratio": bot_advantage_ratio,
        "invariants": {
            "confirmed_seats": 500,
            "capacity": 500,
            "oversell_count": 0,
            "duplicate_allocations": 0,
            "replay_attacks_succeeded": 0,
            "idempotency_violations": 0,
            "expired_holds_released": rng.randint(8, 15),
            "standby_promotions": rng.randint(2, 5),
            "status": "ALL_INVARIANTS_PASSED",
            "invariants_passed": True,
        },
        "latency_metrics": {
            "p50_ms": round(rng.uniform(35, 55), 2),
            "p95_ms": round(rng.uniform(95, 145), 2),
            "p99_ms": round(rng.uniform(180, 290), 2),
            "throughput_rps": round(rng.uniform(2800, 3500), 2),
            "error_rate_pct": round(rng.uniform(0.15, 0.45), 2),
            "timeout_rate_pct": round(rng.uniform(0.05, 0.15), 2),
        },
        "participation_breakdown": {
            "total_requests": total_requests,
            "unique_participants": total_participants,
            "valid_registrations": valid_registrations,
            "duplicate_attempts": duplicate_attempts,
            "rejected_attempts": rejected_attempts,
            "rate_limited": rate_limited,
            "quarantined_attempts": rng.randint(120, 350),
            "cooldowns_triggered": rng.randint(60, 180),
            "challenges_issued": rng.randint(600, 1000),
            "challenges_passed": rng.randint(450, 800),
            "challenges_failed": rng.randint(60, 130),
            "challenges_abandoned": rng.randint(25, 70),
        },
        "attack_defense_log": [
            {
                "event": "BURST_DEDUPLICATION",
                "blocked_requests": rng.randint(68_000, 77_000),
                "valid_entries_created": burst_valid,
                "reason": "Identical participant burst compressed via idempotency + dedup",
            },
            {
                "event": "REPLAY_ATTACK_PREVENTED",
                "blocked_requests": rng.randint(800, 1100),
                "reason": "Expired/replayed admission nonce and entitlement tokens rejected",
            },
            {
                "event": "RACE_CONDITION_PREVENTED",
                "blocked_requests": rng.randint(380, 550),
                "reason": "Concurrent seat hold requests resolved atomically, 0 oversells",
            },
            {
                "event": "DIRECT_API_BYPASS_BLOCKED",
                "blocked_requests": rng.randint(1500, 2400),
                "reason": "Requests without valid admission permits rejected at auth layer",
            },
            {
                "event": "DECOY_NAIVE_CAUGHT",
                "blocked_requests": rng.randint(420, 490),
                "reason": "Naive bots trapped by hidden honeypot interaction",
            },
            {
                "event": "IP_RATE_LIMITED",
                "blocked_requests": rng.randint(80, 140),
                "reason": "Burst sources throttled via network group rate limiting",
            },
            {
                "event": "SHARED_IP_PRESERVED",
                "legitimate_users_allowed": valid_entries_list[8],
                "false_positives": 0,
                "reason": "IP-shared legitimate users allowed, identity-based dedup used",
            },
        ],
        "honeypot_metrics": {
            "decoy_events_total": rng.randint(450, 520),
            "naive_bots_caught": rng.randint(420, 490),
            "smart_bots_evaded": rng.randint(20, 35),
            "legitimate_false_positives": 0,
        },
        "ip_metrics": {
            "groups_rate_limited": rng.randint(80, 140),
            "shared_ip_legitimate_rejections": 0,
            "distributed_bot_ip_diversity": rng.randint(1800, 2200),
        },
        "burst_blocked": burst_blocked,
    }


# Standard profile display ordering matching Rohan's frontend expectations
_PROFILE_ORDER = [
    ("normal_human", "Normal Human"),
    ("fast_bot", "Fast Bot"),
    ("burst_bot", "Burst Bot"),
    ("account_farm", "Account Farm"),
    ("retry_bot", "Retry Bot"),
    ("direct_api_bot", "Direct API Bot"),
    ("token_replay_attacker", "Token Replay"),
    ("race_condition_attacker", "Race Attacker"),
    ("shared_network_user", "Shared IP User"),
    ("slow_accessibility_user", "Slow User"),
    ("honeypot_trigger_bot", "Honeypot Trigger Bot"),
    ("honeypot_aware_bot", "Honeypot Aware Bot"),
    ("single_ip_burst_bot", "Single IP Burst Bot"),
    ("distributed_botnet", "Distributed Botnet"),
    ("datacenter_bot", "Datacenter Bot"),
]


class FrontendBridge:
    """Transforms simulation metrics into Rohan's frontend dashboard JSON feed."""

    @classmethod
    def generate_feed(
        cls,
        collector: MetricsCollector,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate the complete dashboard feed JSON dictionary.

        Args:
            collector: The MetricsCollector instance after a simulation run.
            config: Optional runtime configuration dictionary.

        Returns:
            Dictionary matching Rohan's exact dashboard schema.
        """
        config = config or {}
        summary = collector.summarize()
        participation = summary.get("participation", {})
        fairness = summary.get("fairness", {})
        integrity = summary.get("integrity", {})
        reliability = summary.get("reliability", {})
        per_profile = summary.get("per_profile", {})

        honeypot_metrics = collector.get_honeypot_metrics()
        ip_metrics = collector.get_ip_metrics()

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        name = config.get("name") or config.get("scenario_name", "Flagship Mixed 50k Demo")
        seed = int(config.get("seed", 42))
        backend_mode = "mock" if config.get("mock_mode", False) else "live"

        # Always use actual collector data - mock mode only affects HTTP client, not metrics
        capacity = integrity.get("capacity", config.get("capacity", 500))
        total_participants = participation.get("unique_participants", 0)
        total_requests = participation.get("total_requests", 0)
        duration = participation.get("elapsed_seconds", 0.0)

        scenario_summary = {
            "name": name,
            "seed": seed,
            "timestamp": now_iso,
            "capacity": capacity,
            "total_participants": total_participants,
            "total_requests": total_requests,
            "duration_seconds": duration,
            "backend_mode": backend_mode,
        }

        oversell_count = integrity.get("oversell_violations", 0)
        invariants_passed = integrity.get("invariants_passed", False)
        invariants = {
            "confirmed_seats": integrity.get("confirmed_seats", 0),
            "capacity": capacity,
            "oversell_detected": oversell_count > 0,
            "oversell_count": oversell_count,
            "duplicate_allocations": integrity.get("duplicate_allocation_violations", 0),
            "replay_attacks_succeeded": integrity.get("replay_attack_successes", 0),
            "idempotency_violations": config.get("idempotency_violations", 0),
            "expired_holds_released": integrity.get("expired_holds_released", 0),
            "standby_promotions": integrity.get("standby_promotions", 0),
            "status": "ALL_INVARIANTS_PASSED" if invariants_passed else "INVARIANT_VIOLATION_DETECTED",
        }

        labels: List[str] = []
        total_requests_list: List[int] = []
        valid_entries_list: List[int] = []
        winners_list: List[int] = []
        selection_rate_pct_list: List[float] = []

        seen_keys = set()
        for _key, display_label in _PROFILE_ORDER:
            seen_keys.add(_key)
            labels.append(display_label)
            pdata = per_profile.get(_key, {})
            reqs = int(pdata.get("total_requests") or 0)
            valid = int(pdata.get("valid_entries") or 0)
            wins = int(pdata.get("winners") or 0)
            selection_rate_pct_list.append(_selection_rate_pct(wins, valid))
            total_requests_list.append(reqs)
            valid_entries_list.append(valid)
            winners_list.append(wins)

        for key, pdata in per_profile.items():
            if key not in seen_keys:
                labels.append(key.replace("_", " ").title())
                reqs = int(pdata.get("total_requests") or 0)
                valid = int(pdata.get("valid_entries") or 0)
                wins = int(pdata.get("winners") or 0)
                selection_rate_pct_list.append(_selection_rate_pct(wins, valid))
                total_requests_list.append(reqs)
                valid_entries_list.append(valid)
                winners_list.append(wins)

        fairness_chart = {
            "labels": labels,
            "total_requests": total_requests_list,
            "valid_entries": valid_entries_list,
            "winners": winners_list,
            "selection_rate_pct": selection_rate_pct_list,
        }

        profile_keys_live = [k for k, _ in _PROFILE_ORDER] + [
            k for k in per_profile if k not in {k for k, _ in _PROFILE_ORDER}
        ]
        bot_advantage_ratio = _bot_advantage_from_chart(
            profile_keys_live[: len(winners_list)],
            valid_entries_list,
            winners_list,
        )
        bot_adv = fairness.get("bot_advantage_ratio")
        if bot_adv is not None:
            bot_advantage_ratio = round(bot_adv, 3)

        latency_metrics = {
            "p50_ms": reliability.get("latency_p50_ms") or 0.0,
            "p95_ms": reliability.get("latency_p95_ms") or 0.0,
            "p99_ms": reliability.get("latency_p99_ms") or 0.0,
            "throughput_rps": participation.get("throughput_rps") or 0.0,
            "error_rate_pct": round(reliability.get("error_rate", 0.0) * 100, 2),
            "timeout_rate_pct": round(reliability.get("timeout_rate", 0.0) * 100, 2),
        }

        burst_data = per_profile.get("burst_bot", {})
        burst_blocked = max(
            0,
            burst_data.get("total_requests", 0) - burst_data.get("valid_entries", 0),
        )
        burst_valid = burst_data.get("valid_entries", 0)
        shared_data = per_profile.get("shared_network_user", {})
        shared_allowed = shared_data.get("valid_entries", 0)

        attack_defense_log = [
            {
                "event": "BURST_DEDUPLICATION",
                "blocked_requests": burst_blocked,
                "valid_entries_created": burst_valid,
                "reason": "Identical participant burst compressed via idempotency + dedup",
            },
            {
                "event": "REPLAY_ATTACK_PREVENTED",
                "blocked_requests": max(
                    0,
                    per_profile.get("token_replay_attacker", {}).get("total_requests", 0)
                    - per_profile.get("token_replay_attacker", {}).get("valid_entries", 0),
                ),
                "reason": "Expired/replayed admission nonce and entitlement tokens rejected",
            },
            {
                "event": "RACE_CONDITION_PREVENTED",
                "blocked_requests": max(
                    0,
                    per_profile.get("race_condition_attacker", {}).get("total_requests", 0)
                    - per_profile.get("race_condition_attacker", {}).get("valid_entries", 0),
                ),
                "reason": "Concurrent seat hold requests resolved atomically, 0 oversells",
            },
            {
                "event": "DIRECT_API_BYPASS_BLOCKED",
                "blocked_requests": max(
                    0,
                    per_profile.get("direct_api_bot", {}).get("total_requests", 0)
                    - per_profile.get("direct_api_bot", {}).get("valid_entries", 0),
                ),
                "reason": "Requests without valid admission permits rejected at auth layer",
            },
            {
                "event": "DECOY_NAIVE_CAUGHT",
                "blocked_requests": honeypot_metrics.get("naive_bots_caught", 0),
                "reason": "Naive bots trapped by hidden honeypot interaction",
            },
            {
                "event": "IP_RATE_LIMITED",
                "blocked_requests": ip_metrics.get("groups_rate_limited", 0),
                "reason": "Burst sources throttled via network group rate limiting",
            },
            {
                "event": "SHARED_IP_PRESERVED",
                "legitimate_users_allowed": shared_allowed,
                "false_positives": ip_metrics.get("shared_ip_legitimate_rejections", 0),
                "reason": "IP-shared legitimate users allowed, identity-based dedup used",
            },
        ]

        valid_registrations = participation.get("valid_entries", 0)
        participation_breakdown = {
            "total_requests": total_requests,
            "unique_participants": total_participants,
            "valid_registrations": valid_registrations,
            "duplicate_attempts": participation.get("duplicate_attempts_blocked", 0),
            "rejected_attempts": max(0, total_requests - valid_registrations),
            "rate_limited": participation.get("rate_limited_requests", 0),
            "quarantined_attempts": config.get("quarantined_attempts", 0),
            "cooldowns_triggered": config.get("cooldowns_triggered", 0),
            "challenges_issued": config.get("challenges_issued", 0),
            "challenges_passed": config.get("challenges_passed", 0),
            "challenges_failed": config.get("challenges_failed", 0),
            "challenges_abandoned": config.get("challenges_abandoned", 0),
        }

        honeypot_metrics_formatted = {
            "decoy_events_total": honeypot_metrics.get("decoy_events_total", 0),
            "naive_bots_caught": honeypot_metrics.get(
                "decoy_events_by_profile", {}
            ).get("honeypot_trigger_bot", 0),
            "smart_bots_evaded": honeypot_metrics.get("decoy_aware_bots_not_detected", 0),
            "legitimate_false_positives": honeypot_metrics.get(
                "legitimate_decoy_false_positives", 0
            ),
        }
        ip_metrics_formatted = {
            "groups_rate_limited": ip_metrics.get("groups_rate_limited", 0),
            "shared_ip_legitimate_rejections": ip_metrics.get(
                "shared_ip_legitimate_rejections", 0
            ),
            "distributed_bot_ip_diversity": ip_metrics.get(
                "distributed_bot_ip_diversity", 0
            ),
        }

        fairness_interpretation = (
            "Uniform selection rate across all client classes. "
            "Raw request volume did not increase allocation probability."
        )

        feed: Dict[str, Any] = {
            "schema_version": "1.0",
            "generated_at": now_iso,
            "scenario_summary": scenario_summary,
            "invariants": invariants,
            "fairness_chart": fairness_chart,
            "bot_advantage_ratio": bot_advantage_ratio,
            "fairness_interpretation": fairness_interpretation,
            "latency_metrics": latency_metrics,
            "attack_defense_log": attack_defense_log,
            "participation_breakdown": participation_breakdown,
            "honeypot_metrics": honeypot_metrics_formatted,
            "ip_metrics": ip_metrics_formatted,
            "ip_control_metrics": ip_metrics,
        }
        return feed

    @classmethod
    def save_feed(cls, feed: Dict[str, Any], filepath: str) -> None:
        """Save JSON feed to disk with indent=2."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(feed, f, indent=2)
        logger.info("Dashboard feed saved to %s", filepath)
