"""
Worker runner orchestrating all background worker routines in a single safe execution cycle.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.workers.base import safe_worker_job
from app.workers.cleanup_worker import cleanup_expired_sessions_and_records
from app.workers.entitlement_expiry_worker import expire_stale_entitlements
from app.workers.hold_expiry_worker import expire_stale_seat_holds
from app.workers.standby_promotion_worker import process_standby_promotions

logger = logging.getLogger(__name__)


async def run_all_once() -> dict[str, Any]:
    """
    Executes a complete pass across all Fair Drop background workers:
      1. Seat Hold Expiration
      2. Entitlement Expiration
      3. Standby Queue Promotion
      4. Session & Idempotency Cleanup
    Returns a unified, JSON-serializable statistics summary.
    """
    cycle_start = datetime.now(timezone.utc)
    logger.info("=== Starting background worker pass at %s ===", cycle_start.isoformat())

    hold_results = await safe_worker_job("hold_expiry", expire_stale_seat_holds)
    ent_results = await safe_worker_job("entitlement_expiry", expire_stale_entitlements)
    standby_results = await safe_worker_job("standby_promotion", process_standby_promotions)
    cleanup_results = await safe_worker_job("cleanup", cleanup_expired_sessions_and_records)

    cycle_end = datetime.now(timezone.utc)
    total_duration_ms = (cycle_end - cycle_start).total_seconds() * 1000.0

    summary = {
        "timestamp": cycle_end.isoformat(),
        "total_duration_ms": round(total_duration_ms, 2),
        "workers": {
            "hold_expiry": hold_results,
            "entitlement_expiry": ent_results,
            "standby_promotion": standby_results,
            "cleanup": cleanup_results,
        },
        "all_successful": all(
            w.get("success", False)
            for w in [hold_results, ent_results, standby_results, cleanup_results]
        ),
    }

    logger.info(
        "=== Completed background worker pass in %.2fms (success=%s) ===",
        total_duration_ms,
        summary["all_successful"],
    )

    return summary
