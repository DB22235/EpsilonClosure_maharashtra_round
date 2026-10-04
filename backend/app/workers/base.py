"""
Worker base utilities, logging, and resilient execution wrapper.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.audit import AuditEvent, MetricEvent

logger = logging.getLogger(__name__)


async def safe_worker_job(
    job_name: str,
    func: Callable[[AsyncSession], Coroutine[Any, Any, dict[str, Any]]],
) -> dict[str, Any]:
    """
    Executes a worker job inside an isolated database session with full error isolation.
    If the worker job encounters an unhandled exception, it logs the error, records a
    WORKER_JOB_FAILED AuditEvent, and safely returns failure status without crashing the process.
    """
    job_id = f"job-{job_name}-{uuid.uuid4().hex[:8]}"
    start_time = datetime.now(timezone.utc)
    logger.info("[%s] Worker job '%s' started", job_id, job_name)

    async with async_session_factory() as db:
        try:
            stats = await func(db)
            await db.commit()
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            logger.info(
                "[%s] Worker job '%s' completed in %.2fms. Stats: %s",
                job_id,
                job_name,
                duration_ms,
                stats,
            )
            return {
                "job_id": job_id,
                "job_name": job_name,
                "success": True,
                "duration_ms": round(duration_ms, 2),
                "stats": stats,
            }
        except Exception as exc:
            await db.rollback()
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            logger.error(
                "[%s] Worker job '%s' failed after %.2fms: %s",
                job_id,
                job_name,
                duration_ms,
                exc,
                exc_info=True,
            )
            # Record audit failure in a fresh transaction
            try:
                async with async_session_factory() as error_db:
                    error_db.add(
                        AuditEvent(
                            actor_type="WORKER",
                            event_type="WORKER_JOB_FAILED",
                            request_id=job_id,
                            metadata_json={
                                "job_name": job_name,
                                "error": str(exc),
                                "duration_ms": duration_ms,
                            },
                        )
                    )
                    error_db.add(
                        MetricEvent(
                            metric_name="worker_job_failures_count",
                            metric_value=1.0,
                            tags={"job_name": job_name},
                        )
                    )
                    await error_db.commit()
            except Exception as audit_exc:
                logger.error("[%s] Failed to record error audit event: %s", job_id, audit_exc)

            return {
                "job_id": job_id,
                "job_name": job_name,
                "success": False,
                "duration_ms": round(duration_ms, 2),
                "error": str(exc),
                "stats": {},
            }
