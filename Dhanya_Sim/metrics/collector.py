"""Metrics collection and aggregation for Fair Drop adversarial simulation.

The MetricsCollector aggregates performance, fairness, reliability, and integrity
measurements across simulation runs to produce judge-ready reports and dashboard data.

Primary Metrics Tracked:
1. Participation Metrics:
   - Total requests, unique participants, valid registrations, duplicate attempts,
     rate-limited requests, challenges issued, challenges solved, cooldowns triggered.
2. Fairness Metrics:
   - Winners by client class, valid entries by client class, selection rate by class,
     relative bot advantage ratio, absolute winner-rate difference.
   - Crucial rule: Compare winners against VALID entries, not raw request volume.
3. Integrity Metrics:
   - Confirmed seats count (must be <= capacity).
   - Oversell count (must be exactly 0).
   - Duplicate allocations (must be exactly 0).
   - Replay success count (must be exactly 0).
   - Expired holds released, standby promotions executed.
4. Reliability Metrics:
   - Throughput (RPS), Latency percentiles (P50, P95, P99), error rates, timeout rates,
     recovery rates, false positive rates for shared-network and accessibility personas.
"""

from __future__ import annotations

import asyncio
import csv
import json
import statistics
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Record:
    """Schema for a single request outcome record.

    Attributes:
        request_id: Unique UUID for the request.
        timestamp: Unix epoch timestamp of when the request was initiated.
        profile_type: Client class identifier (e.g. 'normal_human', 'burst_bot').
        is_bot: Whether this profile represents adversarial/automated behaviour.
        endpoint: Relative URL path of the API endpoint called.
        method: HTTP method used.
        status_code: HTTP response status code, or None on network failure.
        outcome: Canonical outcome label (SUCCESS, RATE_LIMITED, CONFLICT,
                 TIMEOUT, NETWORK_ERROR, etc.).
        error_code: Structured error code from the response body, if present.
        latency_ms: Round-trip latency in milliseconds.
        retry_number: Zero-indexed retry attempt number.
        identity_id: Participant identifier string.
        idempotency_key: The idempotency key sent with this request, if any.
        is_winner: True only when the server returned a confirmed seat allocation.
        is_valid_entry: True when this request counts as a legitimate, deduplicated entry.
    """

    request_id: str
    timestamp: float
    profile_type: str
    is_bot: bool
    endpoint: str
    method: str
    status_code: Optional[int]
    outcome: str
    error_code: Optional[str]
    latency_ms: float
    retry_number: int = 0
    identity_id: str = "anonymous"
    idempotency_key: Optional[str] = None
    is_winner: bool = False
    is_valid_entry: bool = False


class MetricsCollector:
    """Collects and aggregates HTTP simulation metrics and invariant assertions.

    Thread-safe via an asyncio.Lock (for async callers) backed by a threading.Lock
    for mixed sync/async use.  All mutation goes through ``record()``.

    Tracks participation, fairness (raw requests vs valid entries vs winners),
    integrity (zero oversell, zero duplicate allocations), and reliability.
    """

    def __init__(self, capacity: int = 500) -> None:
        """Initialise an empty collector.

        Args:
            capacity: Total available seats for the campaign (used to assert
                      that confirmed allocations never exceed this value).
        """
        self._capacity: int = capacity
        self._records: List[Record] = []
        self._lock: threading.Lock = threading.Lock()

        # Integrity event counters – updated externally via dedicated helpers
        self._oversell_count: int = 0
        self._duplicate_allocation_count: int = 0
        self._replay_success_count: int = 0
        self._expired_holds_released: int = 0
        self._standby_promotions: int = 0
        self._start_time: float = time.time()

    # ------------------------------------------------------------------
    # Public mutation API
    # ------------------------------------------------------------------

    def record(self, rec: Record) -> None:
        """Append a completed request Record to the in-memory store.

        Args:
            rec: Fully populated Record dataclass instance.
        """
        with self._lock:
            self._records.append(rec)

    def record_request(self, metric: Dict[str, Any]) -> None:
        """Compatibility shim: build a Record from a raw metric dict and record it.

        Expected keys in ``metric``:
            request_id, timestamp, profile_type, is_bot, endpoint, method,
            status_code, outcome, error_code, latency_ms, retry_number,
            identity_id, idempotency_key, is_winner, is_valid_entry.
        """
        rec = Record(
            request_id=metric.get("request_id", ""),
            timestamp=metric.get("timestamp", time.time()),
            profile_type=metric.get("profile_type", "unknown"),
            is_bot=bool(metric.get("is_bot", False)),
            endpoint=metric.get("endpoint", ""),
            method=metric.get("method", "GET"),
            status_code=metric.get("status_code"),
            outcome=metric.get("outcome", "UNKNOWN"),
            error_code=metric.get("error_code"),
            latency_ms=float(metric.get("latency_ms", 0.0)),
            retry_number=int(metric.get("retry_number", 0)),
            identity_id=metric.get("identity_id", "anonymous"),
            idempotency_key=metric.get("idempotency_key"),
            is_winner=bool(metric.get("is_winner", False)),
            is_valid_entry=bool(metric.get("is_valid_entry", False)),
        )
        self.record(rec)

    def mark_oversell(self) -> None:
        """Increment the oversell violation counter (must remain 0)."""
        with self._lock:
            self._oversell_count += 1

    def mark_duplicate_allocation(self) -> None:
        """Increment the duplicate allocation counter (must remain 0)."""
        with self._lock:
            self._duplicate_allocation_count += 1

    def mark_replay_success(self) -> None:
        """Increment replay-attack success counter (must remain 0)."""
        with self._lock:
            self._replay_success_count += 1

    def mark_hold_expired(self) -> None:
        """Record that an expired hold was released back to inventory."""
        with self._lock:
            self._expired_holds_released += 1

    def mark_standby_promotion(self) -> None:
        """Record a successful standby-to-winner promotion."""
        with self._lock:
            self._standby_promotions += 1

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    def _latencies(self, records: List[Record]) -> List[float]:
        return [r.latency_ms for r in records if r.latency_ms > 0]

    def _percentile(self, values: List[float], p: float) -> Optional[float]:
        if not values:
            return None
        sorted_v = sorted(values)
        idx = int(len(sorted_v) * p / 100)
        idx = min(idx, len(sorted_v) - 1)
        return round(sorted_v[idx], 2)

    def _profile_breakdown(self, records: List[Record]) -> Dict[str, Dict[str, Any]]:
        """Compute per-profile-type participation, fairness, and reliability stats."""
        breakdown: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            pt = rec.profile_type
            if pt not in breakdown:
                breakdown[pt] = {
                    "profile_type": pt,
                    "is_bot": rec.is_bot,
                    "total_requests": 0,
                    "valid_entries": 0,
                    "winners": 0,
                    "rate_limited": 0,
                    "conflicts": 0,
                    "errors": 0,
                    "timeouts": 0,
                    "latencies_ms": [],
                }
            b = breakdown[pt]
            b["total_requests"] += 1
            if rec.is_valid_entry:
                b["valid_entries"] += 1
            if rec.is_winner:
                b["winners"] += 1
            if rec.outcome == "RATE_LIMITED":
                b["rate_limited"] += 1
            elif rec.outcome == "CONFLICT":
                b["conflicts"] += 1
            elif rec.outcome in ("TIMEOUT", "NETWORK_ERROR"):
                b["timeouts"] += 1
            elif rec.outcome.startswith("HTTP_") and rec.status_code and rec.status_code >= 500:
                b["errors"] += 1
            if rec.latency_ms > 0:
                b["latencies_ms"].append(rec.latency_ms)

        # Post-process: derive rates and remove raw latency list
        for b in breakdown.values():
            lats = b.pop("latencies_ms")
            b["p50_ms"] = self._percentile(lats, 50)
            b["p95_ms"] = self._percentile(lats, 95)
            b["p99_ms"] = self._percentile(lats, 99)
            total = b["total_requests"]
            entries = b["valid_entries"]
            b["win_rate_vs_valid_entries"] = (
                round(b["winners"] / entries, 4) if entries > 0 else None
            )
            b["error_rate"] = round((b["errors"] + b["timeouts"]) / total, 4) if total else 0
            b["rate_limit_rate"] = round(b["rate_limited"] / total, 4) if total else 0

        return breakdown

    # ------------------------------------------------------------------
    # Public summary API
    # ------------------------------------------------------------------

    def summarize(self) -> Dict[str, Any]:
        """Aggregate recorded metrics into a comprehensive summary.

        Returns:
            Nested dictionary with sections: participation, fairness,
            integrity, reliability, and per_profile.
        """
        with self._lock:
            records = list(self._records)
            oversell = self._oversell_count
            dup_alloc = self._duplicate_allocation_count
            replay_ok = self._replay_success_count
            exp_holds = self._expired_holds_released
            standby = self._standby_promotions

        if not records:
            return {"status": "NO_DATA", "record_count": 0}

        total = len(records)
        elapsed = time.time() - self._start_time
        throughput_rps = round(total / elapsed, 2) if elapsed > 0 else 0.0

        valid_entries = [r for r in records if r.is_valid_entry]
        winners = [r for r in records if r.is_winner]
        rate_limited = [r for r in records if r.outcome == "RATE_LIMITED"]
        confirmed_seats = len(winners)

        lats = self._latencies(records)
        all_unique_ids = {r.identity_id for r in records}

        # ---- Fairness: compare bot vs human win rates vs valid entries ----
        human_entries = [r for r in valid_entries if not r.is_bot]
        bot_entries = [r for r in valid_entries if r.is_bot]
        human_winners = [r for r in winners if not r.is_bot]
        bot_winners = [r for r in winners if r.is_bot]

        human_win_rate = (
            round(len(human_winners) / len(human_entries), 4) if human_entries else None
        )
        bot_win_rate = (
            round(len(bot_winners) / len(bot_entries), 4) if bot_entries else None
        )
        bot_advantage_ratio: Optional[float] = None
        if human_win_rate and bot_win_rate and human_win_rate > 0:
            bot_advantage_ratio = round(bot_win_rate / human_win_rate, 4)

        # ---- Reliability ----
        error_records = [
            r for r in records
            if r.outcome in ("TIMEOUT", "NETWORK_ERROR")
            or (r.status_code and r.status_code >= 500)
        ]

        # ---- False positive: shared-network / slow users rate-limited ----
        benign_rate_limited = [
            r for r in rate_limited
            if r.profile_type in ("shared_network_user", "slow_accessibility_user")
        ]
        false_positive_rate = (
            round(len(benign_rate_limited) / len(rate_limited), 4)
            if rate_limited else 0.0
        )

        per_profile = self._profile_breakdown(records)

        summary: Dict[str, Any] = {
            "participation": {
                "total_requests": total,
                "unique_participants": len(all_unique_ids),
                "valid_entries": len(valid_entries),
                "duplicate_attempts_blocked": len(
                    [r for r in records if r.outcome == "CONFLICT"]
                ),
                "rate_limited_requests": len(rate_limited),
                "throughput_rps": throughput_rps,
                "elapsed_seconds": round(elapsed, 2),
            },
            "fairness": {
                "confirmed_seats": confirmed_seats,
                "human_valid_entries": len(human_entries),
                "bot_valid_entries": len(bot_entries),
                "human_winners": len(human_winners),
                "bot_winners": len(bot_winners),
                "human_win_rate_vs_entries": human_win_rate,
                "bot_win_rate_vs_entries": bot_win_rate,
                "bot_advantage_ratio": bot_advantage_ratio,
                "note": (
                    "Win rates computed against VALID entries, not raw request volume. "
                    "A ratio near 1.0 indicates fair allocation."
                ),
            },
            "integrity": {
                "capacity": self._capacity,
                "confirmed_seats": confirmed_seats,
                "oversell_violations": oversell,
                "duplicate_allocation_violations": dup_alloc,
                "replay_attack_successes": replay_ok,
                "expired_holds_released": exp_holds,
                "standby_promotions": standby,
                "invariants_passed": (
                    oversell == 0
                    and dup_alloc == 0
                    and replay_ok == 0
                    and confirmed_seats <= self._capacity
                ),
            },
            "reliability": {
                "latency_p50_ms": self._percentile(lats, 50),
                "latency_p95_ms": self._percentile(lats, 95),
                "latency_p99_ms": self._percentile(lats, 99),
                "error_rate": round(len(error_records) / total, 4) if total else 0,
                "timeout_rate": round(
                    len([r for r in records if r.outcome == "TIMEOUT"]) / total, 4
                ) if total else 0,
                "rate_limit_rate": round(len(rate_limited) / total, 4) if total else 0,
                "false_positive_rate_benign_clients": false_positive_rate,
            },
            "per_profile": per_profile,
        }
        return summary

    def export_json(self, path: str) -> None:
        """Export the full metrics summary to a JSON file.

        Args:
            path: Destination filesystem path (will be created if missing).
        """
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        summary = self.summarize()
        with out.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)

    def export_csv(self, path: str) -> None:
        """Export all raw request records to a CSV file for further analysis.

        Args:
            path: Destination filesystem path.
        """
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            records = list(self._records)
        if not records:
            return
        fieldnames = list(asdict(records[0]).keys())
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rec in records:
                writer.writerow(asdict(rec))

    def print_summary(self) -> None:
        """Print a Rich-formatted human-readable summary to stdout."""
        try:
            from rich.console import Console
            from rich.table import Table
            from rich import box

            console = Console()
            summary = self.summarize()

            console.rule("[bold cyan]Fair Drop — Simulation Metrics Report[/bold cyan]")

            # Participation
            p = summary.get("participation", {})
            console.print(f"\n[bold]Participation[/bold]")
            console.print(f"  Total Requests    : {p.get('total_requests')}")
            console.print(f"  Unique Participants: {p.get('unique_participants')}")
            console.print(f"  Valid Entries      : {p.get('valid_entries')}")
            console.print(f"  Throughput (RPS)   : {p.get('throughput_rps')}")

            # Fairness
            f_ = summary.get("fairness", {})
            console.print(f"\n[bold]Fairness[/bold]")
            console.print(f"  Confirmed Seats    : {f_.get('confirmed_seats')}")
            console.print(f"  Human Win Rate     : {f_.get('human_win_rate_vs_entries')}")
            console.print(f"  Bot Win Rate       : {f_.get('bot_win_rate_vs_entries')}")
            console.print(f"  Bot Advantage Ratio: {f_.get('bot_advantage_ratio')}")

            # Integrity
            i = summary.get("integrity", {})
            passed = i.get("invariants_passed", False)
            colour = "green" if passed else "red"
            console.print(f"\n[bold]Integrity[/bold]")
            console.print(f"  Oversell Violations       : {i.get('oversell_violations')}")
            console.print(f"  Duplicate Allocations     : {i.get('duplicate_allocation_violations')}")
            console.print(f"  Replay Attack Successes   : {i.get('replay_attack_successes')}")
            console.print(
                f"  Invariants Passed         : [{colour}]{passed}[/{colour}]"
            )

            # Per-profile table
            per = summary.get("per_profile", {})
            if per:
                table = Table(
                    title="Per-Profile Breakdown",
                    box=box.SIMPLE_HEAVY,
                    show_lines=False,
                )
                table.add_column("Profile", style="cyan")
                table.add_column("Bot?", justify="center")
                table.add_column("Requests", justify="right")
                table.add_column("Valid", justify="right")
                table.add_column("Winners", justify="right")
                table.add_column("Win Rate", justify="right")
                table.add_column("P95 ms", justify="right")
                table.add_column("Err Rate", justify="right")

                for b in per.values():
                    table.add_row(
                        b["profile_type"],
                        "✓" if b["is_bot"] else "—",
                        str(b["total_requests"]),
                        str(b["valid_entries"]),
                        str(b["winners"]),
                        str(b.get("win_rate_vs_valid_entries", "N/A")),
                        str(b.get("p95_ms", "N/A")),
                        str(b.get("error_rate", "N/A")),
                    )
                console.print(table)

        except ImportError:
            # Rich not available, fall back to plain print
            import pprint
            pprint.pprint(self.summarize())
