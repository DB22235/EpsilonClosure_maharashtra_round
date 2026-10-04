"""
Rate limit storage engine and interfaces.

Provides an abstract BaseRateLimitStore with an in-memory sliding window
implementation for development and testing. Designed to be swapped with a Redis
backend without altering downstream route or middleware signatures.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
import logging
import time
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a rate limit check."""
    allowed: bool
    retry_after_seconds: int
    remaining: int
    limit: int
    reset_epoch: int


class BaseRateLimitStore(ABC):
    """Abstract interface for rate limiter storage backends."""

    @abstractmethod
    async def check_and_increment(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        """
        Check if an operation under `key` is allowed and record the attempt if permitted.
        """
        pass

    @abstractmethod
    async def reset(self, key: str | None = None) -> None:
        """
        Reset timestamps for a specific key or all keys (useful for test isolation).
        """
        pass


class InMemoryRateLimitStore(BaseRateLimitStore):
    """
    Thread-safe and async-safe in-memory sliding window rate limiter.
    Stores timestamps of allowed requests per key and evicts timestamps older than window.
    """

    def __init__(self, cleanup_interval_seconds: int = 60) -> None:
        self._store: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = cleanup_interval_seconds

    async def check_and_increment(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        if limit <= 0:
            return RateLimitResult(
                allowed=True,
                retry_after_seconds=0,
                remaining=9999,
                limit=limit,
                reset_epoch=0,
            )

        now = time.time()
        cutoff = now - window_seconds

        async with self._lock:
            # Periodic background cleanup of dead keys
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup_expired(now)

            timestamps = self._store.get(key, [])
            # Filter to active sliding window
            active_timestamps = [t for t in timestamps if t > cutoff]

            if len(active_timestamps) >= limit:
                # Limit exceeded: calculate retry after based on oldest event in current window
                oldest_event = active_timestamps[0]
                retry_after = max(1, int(oldest_event + window_seconds - now + 0.999))
                self._store[key] = active_timestamps
                return RateLimitResult(
                    allowed=False,
                    retry_after_seconds=retry_after,
                    remaining=0,
                    limit=limit,
                    reset_epoch=int(oldest_event + window_seconds),
                )

            # Request permitted: record current event
            active_timestamps.append(now)
            self._store[key] = active_timestamps
            remaining = max(0, limit - len(active_timestamps))
            return RateLimitResult(
                allowed=True,
                retry_after_seconds=0,
                remaining=remaining,
                limit=limit,
                reset_epoch=int(now + window_seconds),
            )

    def _cleanup_expired(self, now: float) -> None:
        """Evict stale keys inactive for > 10 minutes."""
        self._last_cleanup = now
        stale_cutoff = now - 600
        keys_to_remove = []
        for k, ts_list in self._store.items():
            valid = [t for t in ts_list if t > stale_cutoff]
            if not valid:
                keys_to_remove.append(k)
            else:
                self._store[k] = valid
        for k in keys_to_remove:
            del self._store[k]

    async def reset(self, key: str | None = None) -> None:
        async with self._lock:
            if key is None:
                self._store.clear()
            elif key in self._store:
                del self._store[key]


@lru_cache(maxsize=1)
def get_rate_limit_store() -> BaseRateLimitStore:
    """Singleton getter for process-wide rate limiter store."""
    return InMemoryRateLimitStore()
