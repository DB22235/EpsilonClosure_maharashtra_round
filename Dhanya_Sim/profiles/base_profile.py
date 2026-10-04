"""Base client profile for Fair Drop adversarial simulation.

Provides abstract base class BaseProfile with standardized HTTP execution,
request timing, idempotency generation, and structured audit metric recording.
No backend internals or database models are imported; communication is strictly HTTP.
"""

from abc import ABC, abstractmethod
import asyncio
import random
import time
from typing import Any, Dict, List, Optional
import uuid

import httpx


class BaseProfile(ABC):
    """Abstract base class representing a simulated client profile.

    Attributes:
        profile_type: Identifier string for the client class.
        config: Configuration dictionary for target URL, timings, and policies.
        http_client: Asynchronous HTTP/2 client for all network calls.
        results: In-memory audit log of all request attempts.
    """

    profile_type: str = "base_profile"

    def __init__(self, config: Dict[str, Any], http_client: httpx.AsyncClient) -> None:
        """Initialize the client profile.

        Args:
            config: Simulator configuration (e.g. base_url, jitter, timeouts).
            http_client: Async httpx client used for HTTP communication.
        """
        self.config: Dict[str, Any] = config or {}
        self.http_client: httpx.AsyncClient = http_client
        self.base_url: str = self.config.get("base_url", "http://localhost:8000").rstrip("/")
        self.results: List[Dict[str, Any]] = []

    def generate_idempotency_key(self) -> str:
        """Generate a random UUID4 idempotency key."""
        return str(uuid.uuid4())

    async def sim_delay(self, lo: float, hi: float) -> None:
        """Sleep for a realistic human-pacing delay, or near-zero in mock/test mode.

        In mock mode (``config["mock_mode"] is True``) the delay collapses to
        1 ms so that the full test suite completes in seconds rather than minutes.

        Args:
            lo: Minimum sleep duration in seconds (real mode).
            hi: Maximum sleep duration in seconds (real mode).
        """
        if self.config.get("mock_mode", False):
            await asyncio.sleep(0.001)
        else:
            await asyncio.sleep(random.uniform(lo, hi))

    def record_result(
        self,
        response: Optional[httpx.Response],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Record structured request metrics to the in-memory results list.

        Args:
            response: httpx.Response object if network call succeeded, else None.
            metadata: Context dictionary containing request_id, identity_id,
                      idempotency_key, start_time, end_time, retry_number, etc.

        Returns:
            The recorded dictionary record.
        """
        status_code: Optional[int] = response.status_code if response is not None else None
        error_code: Optional[str] = None
        outcome: str = "FAILED"

        if response is not None:
            if 200 <= response.status_code < 300:
                outcome = "SUCCESS"
            elif response.status_code == 429:
                outcome = "RATE_LIMITED"
                error_code = "RATE_LIMITED"
            elif response.status_code == 409:
                outcome = "CONFLICT"
                error_code = "DUPLICATE_OR_CONFLICT"
            else:
                outcome = f"HTTP_{response.status_code}"
                try:
                    payload = response.json()
                    if isinstance(payload, dict):
                        err = payload.get("error")
                        if isinstance(err, dict):
                            error_code = err.get("code")
                        elif isinstance(err, str):
                            error_code = err
                except Exception:
                    pass
        else:
            outcome = metadata.get("error_type", "NETWORK_ERROR")
            error_code = metadata.get("error_code", "CONNECTION_TIMEOUT")

        is_winner = False
        is_valid_entry = False
        endpoint = metadata.get("endpoint", "")
        if response is not None and outcome == "SUCCESS":
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    is_winner = bool(payload.get("is_winner"))
            except Exception:
                pass
            if "/register" in endpoint or "/join" in endpoint:
                is_valid_entry = True

        record = {
            "request_id": metadata.get("request_id") or str(uuid.uuid4()),
            "client_class": self.profile_type,
            "identity_id": metadata.get("identity_id", "anonymous"),
            "idempotency_key": metadata.get("idempotency_key"),
            "status_code": status_code,
            "error_code": error_code,
            "start_time": metadata.get("start_time", time.time()),
            "end_time": metadata.get("end_time", time.time()),
            "retry_number": metadata.get("retry_number", 0),
            "outcome": outcome,
            "endpoint": endpoint,
            "method": metadata.get("method", "GET"),
            "is_winner": is_winner,
            "is_valid_entry": is_valid_entry,
        }
        self.results.append(record)
        return record

    async def send_request(
        self,
        method: str,
        path: str,
        identity_id: str,
        idempotency_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_number: int = 0,
        timeout: Optional[float] = None,
    ) -> Optional[httpx.Response]:
        """Helper to dispatch an HTTP request with automatic metric recording.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Relative URL path (e.g. /api/campaigns/{id}/register)
            identity_id: Participant identifier
            idempotency_key: Idempotency token header
            headers: Additional HTTP headers
            json_data: JSON payload dictionary
            retry_number: Attempt index for retry accounting
            timeout: Optional per-request timeout in seconds

        Returns:
            httpx.Response if successful, None on network exception.
        """
        req_headers: Dict[str, str] = headers.copy() if headers else {}
        if idempotency_key:
            req_headers["Idempotency-Key"] = idempotency_key
        if "X-Request-ID" not in req_headers:
            req_headers["X-Request-ID"] = str(uuid.uuid4())
        if "X-Identity-ID" not in req_headers:
            req_headers["X-Identity-ID"] = identity_id

        url = f"{self.base_url}{path}"
        start_time = time.time()
        response: Optional[httpx.Response] = None
        error_type: Optional[str] = None
        error_code: Optional[str] = None

        try:
            if isinstance(timeout, (int, float)):
                req_timeout: Any = httpx.Timeout(float(timeout), connect=min(5.0, float(timeout)))
            else:
                cfg_timeout = float(self.config.get("timeout", 10.0))
                req_timeout = httpx.Timeout(cfg_timeout, connect=min(5.0, cfg_timeout))

            response = await self.http_client.request(
                method=method,
                url=url,
                headers=req_headers,
                json=json_data,
                timeout=req_timeout,
            )
        except httpx.TimeoutException:
            error_type = "TIMEOUT"
            error_code = "REQUEST_TIMEOUT"
        except httpx.RequestError as exc:
            error_type = "NETWORK_ERROR"
            error_code = exc.__class__.__name__
        except Exception as exc:  # noqa: BLE001
            error_type = "CLIENT_CRASH"
            error_code = exc.__class__.__name__
        finally:
            end_time = time.time()
            self.record_result(
                response=response,
                metadata={
                    "request_id": req_headers.get("X-Request-ID"),
                    "identity_id": identity_id,
                    "idempotency_key": idempotency_key,
                    "start_time": start_time,
                    "end_time": end_time,
                    "retry_number": retry_number,
                    "endpoint": path,
                    "method": method,
                    "error_type": error_type,
                    "error_code": error_code,
                },
            )

        return response

    @abstractmethod
    async def execute_registration_flow(
        self,
        campaign_id: str,
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute the registration workflow for this client persona.

        Args:
            campaign_id: Unique identifier of the campaign.
            identity: Participant credentials and identity metadata.

        Returns:
            Summary dictionary of registration flow results.
        """
        pass

    @abstractmethod
    async def execute_claim_flow(
        self,
        entitlement_id: str,
    ) -> Dict[str, Any]:
        """Execute the seat hold and redemption flow for a winner entitlement.

        Args:
            entitlement_id: Winner entitlement identifier.

        Returns:
            Summary dictionary of claim flow results.
        """
        pass
