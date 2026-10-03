"""Abstract base client for all Fair Drop client profiles.

Every profile inherits BaseClient and implements ``run()``.
All HTTP calls go through ``_request()``, which automatically:
  - Injects the Supabase JWT and X-Request-ID header.
  - Records the outcome to the shared MetricsCollector.
  - Returns (status_code, response_body) for the caller to act on.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

import httpx

from simulator.config import settings
from simulator.metrics.collector import RequestOutcome, collector


class BaseClient(ABC):
    """Abstract HTTP client with auto-logging to MetricsCollector.

    Attributes:
        client_class: Label used in metrics (override in subclasses).
        user:         Dict with keys ``user_id``, ``access_token``, ``email``.
        campaign_id:  UUID of the campaign under test.
        scenario:     Name of the scenario being executed.
        permit:       The admission permit returned by /join, if obtained.
    """

    client_class: str = "base"

    def __init__(
        self,
        user: dict,
        campaign_id: str,
        scenario: str = "unknown",
    ) -> None:
        self.user = user
        self.campaign_id = campaign_id
        self.scenario = scenario
        self.permit: Optional[dict] = None

    # ------------------------------------------------------------------
    # Core transport layer
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        operation: str,
        json_body: Optional[dict] = None,
        idempotency_key: Optional[str] = None,
        retry_number: int = 0,
        extra: Optional[dict] = None,
        override_token: Optional[str] = None,
    ) -> tuple[int, dict]:
        """Send one HTTP request, record the outcome, return (status, body).

        Args:
            method:          HTTP verb ('GET', 'POST', …).
            path:            URL path relative to API_BASE_URL.
            operation:       Logical name for metrics ('join', 'register', …).
            json_body:       Optional JSON payload.
            idempotency_key: Value for Idempotency-Key header.
            retry_number:    Current retry attempt index (0 = first attempt).
            extra:           Extra key-value data attached to the recorded outcome.
            override_token:  Use this JWT instead of self.user['access_token'].

        Returns:
            Tuple of (http_status_code, response_body_dict).
            status_code 0 means a network-level failure occurred.
        """
        url = f"{settings.API_BASE_URL}{path}"
        # Support both 'access_token' (seed fixture format) and 'token' (legacy)
        token = override_token or self.user.get("access_token") or self.user.get("token", "")

        headers: dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "X-Request-ID": str(uuid.uuid4()),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        t0 = time.perf_counter()
        status = 0
        body: dict = {}
        error_code: Optional[str] = None

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0)
            ) as http:
                res = await http.request(method, url, json=json_body, headers=headers)
                status = res.status_code
                body = res.json() if res.content else {}
                if status >= 400:
                    error_code = (
                        body.get("error", {}).get("code")
                        if isinstance(body, dict)
                        else None
                    )
        except Exception as exc:
            status = 0
            body = {"error": {"code": "NETWORK_ERROR", "message": str(exc)}}
            error_code = "NETWORK_ERROR"

        latency_ms = (time.perf_counter() - t0) * 1000.0

        await collector.record(
            RequestOutcome(
                scenario=self.scenario,
                client_class=self.client_class,
                user_id=self.user.get("user_id", "unknown"),
                operation=operation,
                idempotency_key=idempotency_key,
                status_code=status,
                error_code=error_code,
                latency_ms=round(latency_ms, 3),
                timestamp=datetime.now(timezone.utc).isoformat(),
                retry_number=retry_number,
                extra=extra or {},
            )
        )
        return status, body

    # ------------------------------------------------------------------
    # Standard campaign operations (shared by all profiles)
    # ------------------------------------------------------------------

    async def join(self) -> tuple[int, dict]:
        """POST /campaigns/{id}/join — obtain an admission permit."""
        status, body = await self._request(
            "POST",
            f"/campaigns/{self.campaign_id}/join",
            operation="join",
            json_body={},
        )
        if status in (200, 201) and isinstance(body, dict):
            if "admission_token" in body or "permit" in body:
                self.permit = body
        return status, body

    async def register(
        self,
        idempotency_key: Optional[str] = None,
        override_permit: Optional[dict] = None,
    ) -> tuple[int, dict]:
        """POST /campaigns/{id}/register — submit lottery entry."""
        permit = override_permit or self.permit or {}
        payload = {
            "admission_token": permit.get("admission_token", ""),
            "nonce": permit.get("nonce", ""),
        }
        key = idempotency_key or f"reg_{self.user.get('user_id', 'unknown')}_{self.campaign_id}"
        return await self._request(
            "POST",
            f"/campaigns/{self.campaign_id}/register",
            operation="register",
            json_body=payload,
            idempotency_key=key,
        )

    async def get_result(self) -> tuple[int, dict]:
        """GET /campaigns/{id}/result — fetch lottery outcome for this user."""
        return await self._request(
            "GET",
            f"/campaigns/{self.campaign_id}/result",
            operation="result",
        )

    async def get_status(self) -> tuple[int, dict]:
        """GET /campaigns/{id}/status — check campaign state."""
        return await self._request(
            "GET",
            f"/campaigns/{self.campaign_id}/status",
            operation="status",
        )

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def run(self) -> dict:
        """Execute the full profile behaviour for one simulated participant.

        Returns:
            A dict summarising the outcome (keys vary by profile):
            at minimum ``{"client_class": ..., "user_id": ..., "success": bool}``.
        """
