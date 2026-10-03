"""Thread-safe async metrics collector for the Fair Drop live simulator.

Every HTTP call made by any client profile is recorded as a RequestOutcome.
The singleton ``collector`` instance is shared across all profiles within a
scenario run and cleared between runs by the CLI runner.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class RequestOutcome:
    """Schema for a single HTTP request outcome.

    Attributes:
        scenario:        Name of the scenario being run (e.g. 's02_bot_flood').
        client_class:    Profile class label (e.g. 'normal_human', 'burst_bot').
        user_id:         Supabase user UUID of the caller.
        operation:       Logical operation name ('join', 'register', 'result', …).
        idempotency_key: Value of the Idempotency-Key header, if sent.
        status_code:     HTTP response status code (0 = network error / no response).
        error_code:      Structured error code from response body, or None.
        latency_ms:      Round-trip wall-clock time in milliseconds.
        timestamp:       ISO-8601 UTC timestamp at request initiation.
        retry_number:    Zero-indexed retry attempt (0 = first attempt).
        extra:           Arbitrary extra data for profile-specific annotations.
    """

    scenario: str
    client_class: str
    user_id: str
    operation: str
    idempotency_key: Optional[str]
    status_code: int
    error_code: Optional[str]
    latency_ms: float
    timestamp: str
    retry_number: int = 0
    extra: dict = field(default_factory=dict)


class MetricsCollector:
    """Async-safe, in-memory store of RequestOutcome records.

    Usage::

        from metrics.collector import collector

        await collector.record(outcome)   # inside async profile code
        collector.clear()                 # between scenario runs
        collector.dump(Path("out.json"))  # persist to disk
    """

    def __init__(self) -> None:
        self.outcomes: list[RequestOutcome] = []
        self._lock: asyncio.Lock = asyncio.Lock()

    async def record(self, outcome: RequestOutcome) -> None:
        """Append a RequestOutcome in a concurrency-safe manner."""
        async with self._lock:
            self.outcomes.append(outcome)

    def clear(self) -> None:
        """Reset the collector for the next scenario run."""
        self.outcomes.clear()

    def dump(self, path: Path) -> None:
        """Persist all outcomes to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([asdict(o) for o in self.outcomes], indent=2),
            encoding="utf-8",
        )

    def all_outcomes(self) -> list[RequestOutcome]:
        """Return a snapshot of all recorded outcomes (not a live reference)."""
        return list(self.outcomes)

    def __len__(self) -> int:
        return len(self.outcomes)


# Module-level singleton shared by all profiles and scenarios
collector = MetricsCollector()
