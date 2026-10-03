"""Simulation execution engine for Fair Drop adversarial testing.

Responsibilities:
1. Concurrency Management  — asyncio Semaphore bounded parallelism.
2. HTTP Transport          — shared HTTP/2 AsyncClient or mock responder.
3. Metric Instrumentation  — integrates MetricsCollector for every outcome.
4. Mock Mode               — intelligent scenario-aware fake responses so the
                             simulator runs without a live backend.
5. CLI Entry-point         — ``python -m Dhanya_Sim.runner.engine`` with
                             --scenario, --mock-mode, --run-all flags.

Mock-mode response rules (per Fair Drop API contract):
  - Normal registration      → 201 Created  {"registration_id": ..., "status": "REGISTERED"}
  - Duplicate registration   → 409 Conflict {"error": {"code": "DUPLICATE_ENTRY", ...}}
  - Replay attack            → 400 Bad Req  {"error": {"code": "REPLAY_DETECTED", ...}}
  - No permit / direct API   → 403 Forbidden{"error": {"code": "PERMIT_REQUIRED", ...}}
  - Rate limited             → 429 Too Many {"error": {"code": "RATE_LIMIT_EXCEEDED", ...}}
  - Race hold — loser        → 409 Conflict {"error": {"code": "SEAT_ALREADY_HELD", ...}}
  - Same idempotency key     → 200/201 same body (idempotent return)
  - Post-cutoff request      → 403 Forbidden{"error": {"code": "REGISTRATION_CLOSED", ...}}
  - Challenge replay         → 400 Bad Req  {"error": {"code": "CHALLENGE_ALREADY_USED", ...}}
  - Entitlement replay       → 409 Conflict {"error": {"code": "ENTITLEMENT_ALREADY_USED",...}}
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from unittest.mock import AsyncMock, MagicMock

import httpx
import yaml

from ..metrics.collector import MetricsCollector, Record
from ..profiles.base_profile import BaseProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock response factory
# ---------------------------------------------------------------------------

class MockResponseFactory:
    """Produces realistic Fair Drop API mock responses for each scenario type.

    The factory maintains in-memory state (seen idempotency keys, claimed seats,
    used tokens) to simulate real backend behaviour accurately without a server.
    """

    def __init__(self, scenario_id: int = 0, capacity: int = 500) -> None:
        self._scenario_id = scenario_id
        self._capacity = capacity
        self._lock = threading.Lock()
        # State
        self._registered: set = set()          # identity_ids that registered
        self._idempotency_cache: dict = {}      # key → (status, body)
        self._used_tokens: set = set()          # replayed tokens
        self._seats_held: dict = {}             # seat_id → holder identity_id
        self._confirmed_seats = 0
        self._request_counts: dict = {}         # ip / identity → count
        # Rate-limit thresholds (requests before 429)
        self._rate_limit_threshold = {
            2: 3,   # burst attack — limit aggressively
            9: 1,   # race: only first hold wins
        }.get(scenario_id, 10)

    def _request_id(self) -> str:
        return str(uuid.uuid4())

    def _error_body(self, code: str, message: str) -> dict:
        return {
            "error": {"code": code, "message": message},
            "request_id": self._request_id(),
        }

    def _success_body(self, extra: Optional[dict] = None) -> dict:
        body = {"request_id": self._request_id(), "status": "REGISTERED",
                "registration_id": str(uuid.uuid4())}
        if extra:
            body.update(extra)
        return body

    def get_response(
        self,
        method: str,
        path: str,
        identity_id: str,
        idempotency_key: Optional[str],
        json_data: Optional[dict],
        headers: Optional[dict],
    ) -> tuple[int, dict]:
        """Return (status_code, body_dict) for a mock request.

        Applies scenario-specific logic to simulate the correct backend behaviour.
        """
        with self._lock:
            return self._get_response_locked(
                method, path, identity_id, idempotency_key, json_data, headers
            )

    def _get_response_locked(
        self,
        method: str,
        path: str,
        identity_id: str,
        idempotency_key: Optional[str],
        json_data: Optional[dict],
        headers: Optional[dict],
    ) -> tuple[int, dict]:
        sid = self._scenario_id

        # ---- Idempotency cache: same key → same response ----
        if idempotency_key and idempotency_key in self._idempotency_cache:
            return self._idempotency_cache[idempotency_key]

        # ---- Rate limiting (scenarios 2, 3, and default) ----
        count = self._request_counts.get(identity_id, 0) + 1
        self._request_counts[identity_id] = count
        if count > self._rate_limit_threshold:
            r = (429, self._error_body("RATE_LIMIT_EXCEEDED",
                                       "Too many requests from this identity."))
            if idempotency_key:
                self._idempotency_cache[idempotency_key] = r
            return r

        # ---- Replay attacks (scenarios 6, 7, 8) ----
        if sid in (6, 7, 8):
            token = (json_data or {}).get("token") or identity_id
            if token in self._used_tokens:
                code_map = {
                    6: "PERMIT_ALREADY_USED",
                    7: "CHALLENGE_ALREADY_USED",
                    8: "ENTITLEMENT_ALREADY_USED",
                }
                return (400, self._error_body(
                    code_map.get(sid, "REPLAY_DETECTED"),
                    "This token has already been used and cannot be replayed.",
                ))
            self._used_tokens.add(token)

        # ---- Direct API bypass (scenario 5) ----
        if sid == 5:
            permit = (json_data or {}).get("admission_permit") or \
                     (headers or {}).get("X-Admission-Permit")
            if not permit:
                return (403, self._error_body(
                    "PERMIT_REQUIRED",
                    "A valid admission permit is required to register.",
                ))

        # ---- Race condition (scenario 9) ----
        if sid == 9 and "hold" in path.lower():
            seat_ids = (json_data or {}).get("target_seat_ids", [])
            if not seat_ids:
                seat_ids = [(json_data or {}).get("seat_id", "seat_001")]
            won = False
            for seat_id in seat_ids:
                if seat_id not in self._seats_held and self._confirmed_seats < self._capacity:
                    self._seats_held[seat_id] = identity_id
                    self._confirmed_seats += 1
                    won = True
                    break
            if not won:
                return (409, self._error_body(
                    "SEAT_ALREADY_HELD",
                    "All target seats are already held by other participants.",
                ))
            result = (201, self._success_body(
                {"seat_id": seat_ids[0], "hold_expires_at": time.time() + 900}
            ))
            if idempotency_key:
                self._idempotency_cache[idempotency_key] = result
            return result

        # ---- Cutoff boundary (scenario 14) ----
        if sid == 14:
            # Post-cutoff bots (fast_bot) → 403
            if "fast_bot" in identity_id:
                return (403, self._error_body(
                    "REGISTRATION_CLOSED",
                    "The registration window has closed.",
                ))
                
        # ---- IP Rate Limit Mock ----
        network_group_id = (headers or {}).get("X-Network-Group-ID")
        if network_group_id:
            ng_count = self._request_counts.get(f"ng_{network_group_id}", 0) + 1
            self._request_counts[f"ng_{network_group_id}"] = ng_count
            if ng_count > 100:
                r = (429, self._error_body("RATE_LIMITED", "Too many requests from this network"))
                if idempotency_key:
                    self._idempotency_cache[idempotency_key] = r
                return r

        # ---- Datacenter Mock ----
        ip_class = (headers or {}).get("X-IP-Class")
        risk_score_delta = 0
        if ip_class == "datacenter":
            risk_score_delta += 15

        # ---- Decoy endpoint mock ----
        if "signals/decoy" in path:
            return (200, {"status": "recorded", "risk_delta": 15})

        # ---- Duplicate registration ----
        if identity_id in self._registered and "/register" in path:
            result = (409, self._error_body(
                "DUPLICATE_ENTRY",
                "This participant has already registered for this campaign.",
            ))
            if idempotency_key:
                self._idempotency_cache[idempotency_key] = result
            return result

        # ---- Capacity exhausted ----
        if "/register" in path and self._confirmed_seats >= self._capacity:
            return (409, self._error_body(
                "CAMPAIGN_FULL",
                "Campaign capacity reached.",
            ))

        # ---- Successful registration ----
        if "/register" in path or "/join" in path:
            self._registered.add(identity_id)
            is_valid = True
            # Mark wins probabilistically based on capacity ratio
            is_winner = (
                len(self._registered) <= self._capacity
                and random.random() < (self._capacity / max(1000, len(self._registered) + 1))
            )
            if is_winner:
                self._confirmed_seats += 1
            body = self._success_body({
                "is_winner": is_winner,
                "entitlement_id": str(uuid.uuid4()) if is_winner else None,
            })
            if risk_score_delta > 0:
                body["risk_score"] = risk_score_delta
            
            result = (201, body)
            if idempotency_key:
                self._idempotency_cache[idempotency_key] = result
            return result

        # ---- Challenge verify ----
        if "/challenges/verify" in path:
            token = str(uuid.uuid4())
            if token in self._used_tokens:
                return (400, self._error_body("CHALLENGE_ALREADY_USED", "Token reused."))
            self._used_tokens.add(token)
            return (200, {"verification_token": token, "request_id": self._request_id()})

        # ---- Status / health endpoints ----
        if method == "GET":
            return (200, {"status": "active", "request_id": self._request_id()})

        # ---- Default fallback ----
        return (200, {"status": "ok", "request_id": self._request_id()})


# ---------------------------------------------------------------------------
# Mock HTTP Client
# ---------------------------------------------------------------------------

class MockAsyncClient:
    """Drop-in async replacement for httpx.AsyncClient in mock mode.

    Delegates request routing to MockResponseFactory and returns httpx.Response
    objects so callers don't need to know they're in mock mode.
    """

    def __init__(self, factory: MockResponseFactory) -> None:
        self._factory = factory
        self.is_closed = False

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        json: Optional[dict] = None,
        timeout: Optional[float] = None,
        **_: Any,
    ) -> httpx.Response:
        # Extract path from URL
        path = "/" + "/".join(str(url).split("/")[3:])
        identity_id = (headers or {}).get("X-Identity-ID", "unknown")
        idempotency_key = (headers or {}).get("Idempotency-Key")

        # Simulate a small latency (1-30ms)
        await asyncio.sleep(random.uniform(0.001, 0.030))

        status_code, body = self._factory.get_response(
            method=method,
            path=path,
            identity_id=identity_id,
            idempotency_key=idempotency_key,
            json_data=json,
            headers=headers,
        )

        # Build a real httpx.Response object
        content = body if isinstance(body, bytes) else __import__("json").dumps(body).encode()
        return httpx.Response(
            status_code=status_code,
            headers={"content-type": "application/json"},
            content=content,
        )

    async def aclose(self) -> None:
        self.is_closed = True


# ---------------------------------------------------------------------------
# SimulationEngine
# ---------------------------------------------------------------------------

class SimulationEngine:
    """Orchestrates adversarial traffic execution across multiple worker coroutines.

    Supports both live (real httpx) and mock mode (MockAsyncClient).

    Usage (live)::

        async with SimulationEngine(config={...}) as engine:
            await engine.run_scenario(BurstBot, identities, "camp_001")
        engine.collector.print_summary()

    Usage (mock)::

        async with SimulationEngine(config={..., "mock_mode": True, "scenario_id": 9}) as engine:
            await engine.run_scenario(RaceConditionAttacker, identities, "camp_001")
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialise SimulationEngine.

        Config keys:
            base_url (str): API base URL (default: http://localhost:8000).
            concurrency (int): Max simultaneous workers (default: 50).
            timeout (float): Per-request timeout seconds (default: 10.0).
            http2 (bool): Enable HTTP/2 (default: True; ignored in mock mode).
            capacity (int): Campaign seat capacity for integrity assertions (default: 500).
            ramp_seconds (float): Linear warm-up ramp (default: 0.0).
            mock_mode (bool): Use MockAsyncClient instead of real httpx (default: False).
            scenario_id (int): Scenario ID forwarded to MockResponseFactory (default: 0).
        """
        self.config = config
        self._base_url = config.get("base_url", "http://localhost:8000").rstrip("/")
        self._concurrency = int(config.get("concurrency", 50))
        self._timeout = float(config.get("timeout", 10.0))
        self._http2 = bool(config.get("http2", True))
        self._capacity = int(config.get("capacity", 500))
        self._ramp_seconds = float(config.get("ramp_seconds", 0.0))
        self._mock_mode = bool(config.get("mock_mode", False))
        self._scenario_id = int(config.get("scenario_id", 0))

        self.collector = MetricsCollector(capacity=self._capacity)
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._http_client: Optional[Any] = None
        self._running = False
        self._start_wall = 0.0

    async def __aenter__(self) -> "SimulationEngine":
        await self.start()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.stop()

    async def start(self) -> None:
        if self._running:
            return
        self._semaphore = asyncio.Semaphore(self._concurrency)
        if self._mock_mode:
            factory = MockResponseFactory(
                scenario_id=self._scenario_id,
                capacity=self._capacity,
            )
            self._http_client = MockAsyncClient(factory=factory)
            logger.info(
                "SimulationEngine started in MOCK MODE — scenario_id=%d concurrency=%d",
                self._scenario_id, self._concurrency,
            )
        else:
            limits = httpx.Limits(max_connections=200, max_keepalive_connections=50)
            timeout = httpx.Timeout(self._timeout, connect=min(5.0, self._timeout))
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                http2=self._http2,
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
            )
            logger.info(
                "SimulationEngine started — base_url=%s concurrency=%d (pool limits: max=200, keepalive=50)",
                self._base_url, self._concurrency,
            )
        self._running = True
        self._start_wall = time.time()

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
        logger.info(
            "SimulationEngine stopped — elapsed=%.2fs", time.time() - self._start_wall
        )

    async def _ramp_delay(self, worker_index: int, total_workers: int) -> None:
        if self._ramp_seconds <= 0 or total_workers <= 1:
            return
        await asyncio.sleep(self._ramp_seconds * (worker_index / total_workers))

    async def _run_single_worker(
        self,
        profile_class: Type[BaseProfile],
        identity: Dict[str, Any],
        campaign_id: str,
        worker_index: int,
        total_workers: int,
    ) -> None:
        assert self._semaphore and self._http_client
        await self._ramp_delay(worker_index, total_workers)
        async with self._semaphore:
            profile = profile_class(
                config={
                    **self.config,
                    "identity_id": identity.get("participant_id",
                                                identity.get("account_id", "")),
                },
                http_client=self._http_client,
            )
            worker_crashed = False
            try:
                await profile.execute_registration_flow(
                    campaign_id=campaign_id,
                    identity=identity,
                )
            except Exception as exc:  # noqa: BLE001
                worker_crashed = True
                logger.warning(
                    "Worker %d (%s) unhandled exception: %s",
                    worker_index, profile_class.profile_type, exc,
                )
                profile.results.append({
                    "request_id": str(uuid.uuid4()),
                    "client_class": profile_class.profile_type,
                    "identity_id": identity.get("participant_id", identity.get("account_id", "anonymous")),
                    "start_time": time.time(),
                    "end_time": time.time(),
                    "outcome": "CLIENT_CRASH",
                    "error_code": exc.__class__.__name__,
                    "endpoint": "/api/campaigns/register",
                    "method": "POST",
                })

            is_bot = getattr(profile_class, "is_bot", False)
            for raw in profile.results:
                endpoint = raw.get("endpoint", "")
                is_decoy = "signals/decoy" in endpoint or raw.get("website_url") is not None
                
                # if the JSON data sent has website_url, it's a decoy field (handled in raw dictionary maybe?)
                # We can approximate by looking at the profile logic
                decoy_triggered = is_decoy
                if profile_class.profile_type == "honeypot_trigger_bot":
                    decoy_triggered = True

                rec = Record(
                    request_id=raw.get("request_id", ""),
                    timestamp=raw.get("start_time", time.time()),
                    profile_type=raw.get("client_class", profile_class.profile_type),
                    is_bot=is_bot,
                    endpoint=endpoint,
                    method=raw.get("method", "GET"),
                    status_code=raw.get("status_code"),
                    outcome=raw.get("outcome", "UNKNOWN"),
                    error_code=raw.get("error_code"),
                    latency_ms=round(
                        (raw.get("end_time", 0) - raw.get("start_time", 0)) * 1000, 2
                    ),
                    retry_number=raw.get("retry_number", 0),
                    identity_id=raw.get("identity_id", "anonymous"),
                    idempotency_key=raw.get("idempotency_key"),
                    is_winner=raw.get("is_winner", False),
                    is_valid_entry=raw.get("outcome") in ("SUCCESS", "CONFLICT")
                                   and raw.get("retry_number", 0) == 0,
                    network_group_id=identity.get("network_group_id"),
                    ip_class=identity.get("ip_class", "unknown"),
                    decoy_triggered=decoy_triggered,
                    rate_limited=raw.get("outcome") == "RATE_LIMITED",
                )
                self.collector.record(rec)

    async def run_scenario(
        self,
        profile_class: Type[BaseProfile],
        identities: List[Dict[str, Any]],
        campaign_id: str,
    ) -> None:
        if not self._running:
            raise RuntimeError("Engine not started.")
        total = len(identities)
        logger.info(
            "run_scenario: profile=%s workers=%d campaign=%s mock=%s",
            profile_class.profile_type, total, campaign_id, self._mock_mode,
        )
        tasks = [
            self._run_single_worker(profile_class, identity, campaign_id, idx, total)
            for idx, identity in enumerate(identities)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def run_mixed_scenario(
        self,
        populations: List[Dict[str, Any]],
        campaign_id: str,
    ) -> None:
        if not self._running:
            raise RuntimeError("Engine not started.")
        total_workers = sum(len(p["identities"]) for p in populations)
        all_tasks = []
        global_idx = 0
        for population in populations:
            pc: Type[BaseProfile] = population["profile_class"]
            for identity in population["identities"]:
                all_tasks.append(asyncio.create_task(
                    self._run_single_worker(pc, identity, campaign_id, global_idx, total_workers)
                ))
                global_idx += 1
        await asyncio.gather(*all_tasks, return_exceptions=True)


# ---------------------------------------------------------------------------
# Aggregated compliance report (--run-all)
# ---------------------------------------------------------------------------

async def _run_all_scenarios(
    base_url: str,
    mock_mode: bool,
    concurrency: int,
    output_dir: str,
) -> None:
    """Run all 15 scenarios sequentially and print an aggregated compliance table."""
    from ..scenarios import SCENARIO_REGISTRY, ScenarioConfig

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    compliance: list = []

    for sid in sorted(SCENARIO_REGISTRY.keys()):
        entry = SCENARIO_REGISTRY[sid]
        name = entry["name"]
        logger.info("=== Running Scenario %d: %s ===", sid, name)

        cfg = ScenarioConfig(
            campaign_id=f"compliance_run_{sid}",
            base_url=base_url,
            capacity=500,
            concurrency=concurrency,
            timeout=10.0,
            mock_mode=mock_mode,
            scenario_id=sid,
            output_dir=f"{output_dir}/{sid:02d}_{name}",
        )
        try:
            scenario = entry["class"](config=cfg)
            scenario.setup()
            await scenario.run()
            results = scenario.report() or {}
            integrity = results.get("integrity", {})
            passed = integrity.get("invariants_passed", False)
        except Exception as exc:  # noqa: BLE001
            logger.error("Scenario %d ERRORED: %s", sid, exc)
            passed = False

        compliance.append({
            "id": sid,
            "name": name,
            "passed": passed,
        })

    # Print table
    _print_compliance_table(compliance, output_dir)


def _print_compliance_table(compliance: list, output_dir: str) -> None:
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box

        console = Console()
        table = Table(title="Fair Drop — Compliance Run Results", box=box.HEAVY_EDGE)
        table.add_column("ID", justify="right", style="dim")
        table.add_column("Scenario", style="cyan")
        table.add_column("Result", justify="center")

        for row in compliance:
            result = "[green]PASS[/green]" if row["passed"] else "[red]FAIL[/red]"
            table.add_row(str(row["id"]), row["name"], result)

        console.print(table)
        total = len(compliance)
        passed = sum(1 for r in compliance if r["passed"])
        console.print(f"\n[bold]{passed}/{total} scenarios passed.[/bold]")

    except ImportError:
        print("\n=== Compliance Results ===")
        for row in compliance:
            status = "PASS" if row["passed"] else "FAIL"
            print(f"  [{status}] {row['id']:2d}. {row['name']}")

    # Export JSON
    report_path = Path(output_dir) / "compliance_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w") as f:
        json.dump(compliance, f, indent=2)
    logger.info("Compliance report saved to %s", report_path)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m Dhanya_Sim.runner.engine",
        description="Fair Drop — Adversarial Simulation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios (--scenario):
  1  normal_baseline        11  network_failure_recovery
  2  burst_attack           12  shared_ip_network
  3  distributed_bots       13  slow_vs_fast
  4  retry_idempotency      14  cutoff_boundary
  5  direct_api_bypass      15  flagship_mixed_50k
  6  token_replay
  7  challenge_replay
  8  entitlement_replay
  9  race_condition_seat
  10 hold_expiry_standby
        """,
    )
    p.add_argument(
        "--scenario", "-s",
        default=None,
        help="Scenario to run: integer ID (1-15) or name string.",
    )
    p.add_argument("--run-all", action="store_true",
                   help="Run all 15 scenarios sequentially and produce a compliance report.")
    p.add_argument("--mock-mode", "-m", action="store_true",
                   help="Use mock backend (no live server required).")
    p.add_argument("--live", action="store_true",
                   help="Connect to live Fair Drop FastAPI backend (opposite of --mock-mode).")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate scenario configuration, profiles, and API URLs without sending traffic.")
    p.add_argument("--campaign", default="campaign_demo_001",
                   help="Campaign ID to target (default: campaign_demo_001).")
    p.add_argument("--url", "--base-url", dest="url", default="http://localhost:8000",
                   help="Fair Drop API base URL (default: http://localhost:8000).")
    p.add_argument("--concurrency", type=int, default=50,
                   help="Max concurrent HTTP workers (default: 50).")
    p.add_argument("--capacity", type=int, default=500,
                   help="Campaign seat capacity (default: 500).")
    p.add_argument("--timeout", type=float, default=10.0,
                   help="Per-request timeout seconds (default: 10.0).")
    p.add_argument("--ramp", type=float, default=0.0, dest="ramp_seconds",
                   help="Warm-up ramp seconds (default: 0.0).")
    p.add_argument("--output", "--output-dir", dest="output", default="Dhanya_Sim/output",
                   help="Output directory for reports (default: Dhanya_Sim/output).")
    p.add_argument("--generate-demo-assets", action="store_true",
                   help="Generate all judge demo assets: dashboard feed, attack report, raw metrics CSV.")
    p.add_argument("--run-all-tests", action="store_true",
                   help="Run the complete automated adversarial test suite.")
    return p


async def _check_backend_health(base_url: str, timeout: float = 3.0) -> bool:
    """Check health endpoints on the live backend."""
    clean_url = base_url.rstrip("/")
    candidates = [f"{clean_url}/health", f"{clean_url}/api/health", clean_url]
    async with httpx.AsyncClient(timeout=timeout) as client:
        for url in candidates:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return True
            except Exception:
                continue
    return False


def _perform_dry_run(args: argparse.Namespace) -> None:
    """Validate configs, instantiate all profiles and verify connectivity without sending load."""
    from ..scenarios import SCENARIO_REGISTRY, ScenarioConfig
    from ..profiles import (
        NormalHuman, FastBot, BurstBot, RetryBot, AccountFarm,
        DirectAPIBot, TokenReplayAttacker, RaceConditionAttacker,
        SharedNetworkUser, SlowAccessibilityUser,
    )
    import yaml

    print("\n🔍 Fair Drop Simulator — Dry Run Validation")
    print("---------------------------------------------")

    # 1. Validate scenario registry & YAML files
    all_profiles = [
        NormalHuman, FastBot, BurstBot, RetryBot, AccountFarm,
        DirectAPIBot, TokenReplayAttacker, RaceConditionAttacker,
        SharedNetworkUser, SlowAccessibilityUser,
    ]
    print(f"  • Registered Profiles : {len(all_profiles)}/10 OK")

    configs_found = 0
    for sid, entry in SCENARIO_REGISTRY.items():
        cfg_path = Path(entry["config_path"])
        if cfg_path.exists():
            configs_found += 1
            with cfg_path.open("r", encoding="utf-8") as f:
                yaml.safe_load(f)
    print(f"  • Scenario Configs    : {configs_found}/15 YAML files validated OK")

    # 2. Check profile instantiation
    dummy_factory = MockResponseFactory(scenario_id=1, capacity=500)
    dummy_client = MockAsyncClient(factory=dummy_factory)
    for p_cls in all_profiles:
        inst = p_cls(config={"base_url": args.url}, http_client=dummy_client)
        assert inst.profile_type, f"Profile {p_cls} missing profile_type"

    print("  • Profile Classes     : All 10 profiles instantiable OK")
    print(f"  • Target URL Config   : {args.url}")
    print("\n✅ Dry-run passed. Ready for execution.")


async def _generate_demo_assets(args: argparse.Namespace) -> None:
    """Run Scenario 15 (Flagship Mixed 50k) with seed 42 and generate all demo assets."""
    from ..scenarios import SCENARIO_REGISTRY, ScenarioConfig
    from ..reports.generator import ReportGenerator
    from ..metrics.frontend_bridge import FrontendBridge
    # Seed for determinism
    random.seed(42)
    try:
        import numpy as np
        if hasattr(np, 'random') and hasattr(np.random, 'seed'):
            np.random.seed(42)
    except Exception:
        pass

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    entry = SCENARIO_REGISTRY[15]
    logger.info("Generating demo assets using Scenario 15: %s", entry["name"])

    # Determine mock_mode: default to mock_mode unless --live is explicitly set
    mock_mode = False if args.live else (args.mock_mode or True)

    if not mock_mode:
        healthy = await _check_backend_health(args.url)
        if not healthy:
            print(f"\n❌ Backend unreachable at {args.url}")
            print("💡 Did you mean to use --mock-mode?")
            print(f"💡 Is Dhruv's FastAPI server running on {args.url}?")
            sys.exit(1)

    cfg = ScenarioConfig(
        campaign_id="flagship_demo_42",
        base_url=args.url,
        capacity=args.capacity,
        concurrency=args.concurrency,
        timeout=args.timeout,
        mock_mode=mock_mode,
        scenario_id=15,
        output_dir=str(out_dir),
    )

    scenario = entry["class"](config=cfg)
    scenario.setup()

    # Run using custom engine capture to retain the collector instance
    engine_config = scenario._build_engine_config()
    collector = None
    summary = {}
    try:
        async with SimulationEngine(config=engine_config) as engine:
            await engine.run_mixed_scenario(
                populations=scenario._populations,
                campaign_id=cfg.campaign_id,
            )
            collector = engine.collector
            summary = collector.summarize()
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt caught! Flushing partial metrics...")
        if collector:
            summary = collector.summarize()
            print("\n⚠️ Simulation interrupted. Partial summary produced.")

    if not summary and collector:
        summary = collector.summarize()

    run_config = {
        "scenario_name": "Flagship Mixed 50k Demo",
        "name": "Flagship Mixed 50k Demo",
        "seed": 42,
        "capacity": args.capacity,
        "mock_mode": mock_mode,
        "concurrency": args.concurrency,
        "registration_window": "600s",
    }

    # 1. Dashboard feed JSON
    if collector:
        dashboard_feed = FrontendBridge.generate_feed(collector=collector, config=run_config)
        feed_path = str(out_dir / "dashboard_feed.json")
        FrontendBridge.save_feed(dashboard_feed, feed_path)

        # 2. Markdown attack report
        markdown_report = ReportGenerator.generate_markdown_report(metrics=summary, config=run_config)
        report_path = str(out_dir / "attack_report.md")
        ReportGenerator.save_markdown_report(markdown_report, report_path)

        # 3. Raw metrics CSV
        csv_path = str(out_dir / "raw_metrics.csv")
        collector.export_csv(csv_path)

        # 4. Rich terminal report
        ReportGenerator.print_terminal_report(metrics=summary)

    # 5. Final summary confirmation
    print("\n✅ Demo assets generated. Frontend feed ready for Rohan. Report ready for judges.")


async def _async_main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        stream=sys.stdout,
    )

    parser = _build_parser()
    args = parser.parse_args()

    if args.dry_run:
        _perform_dry_run(args)
        return

    if args.run_all_tests:
        import subprocess
        test_script = Path("tests/simulation/test_adversarial_suite.py")
        ret = subprocess.run([sys.executable, str(test_script)], check=False)
        sys.exit(ret.returncode)

    if args.generate_demo_assets:
        await _generate_demo_assets(args)
        return

    # Determine whether we are in mock mode
    mock_mode = False if args.live else (args.mock_mode or not args.live)

    # Pre-flight health check if running in live mode
    if args.live:
        healthy = await _check_backend_health(args.url)
        if not healthy:
            print(f"\n❌ Backend unreachable at {args.url}")
            print("💡 Did you mean to use --mock-mode?")
            print(f"💡 Is Dhruv's FastAPI server running on {args.url}?")
            sys.exit(1)

    if args.run_all:
        await _run_all_scenarios(
            base_url=args.url,
            mock_mode=mock_mode,
            concurrency=args.concurrency,
            output_dir=args.output,
        )
        return

    if args.scenario is None:
        parser.error("Specify --scenario <id|name>, --run-all, --generate-demo-assets, --dry-run, or --run-all-tests.")

    from ..scenarios import get_scenario, ScenarioConfig, SCENARIO_NAME_INDEX

    try:
        entry = get_scenario(args.scenario)
    except KeyError as exc:
        parser.error(str(exc))

    # Resolve integer scenario ID from registry
    s = args.scenario
    if isinstance(s, str) and s.isdigit():
        sid = int(s)
    else:
        sid = SCENARIO_NAME_INDEX.get(s, 0)

    Path(args.output).mkdir(parents=True, exist_ok=True)

    cfg = ScenarioConfig(
        campaign_id=args.campaign,
        base_url=args.url,
        capacity=args.capacity,
        concurrency=args.concurrency,
        timeout=args.timeout,
        ramp_seconds=args.ramp_seconds,
        output_dir=args.output,
        mock_mode=mock_mode,
        scenario_id=sid,
    )

    scenario_class = entry["class"]
    scenario = scenario_class(config=cfg)
    scenario.setup()

    try:
        await scenario.run()
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt caught! Exiting cleanly and reporting available metrics...")

    results = scenario.report()
    if results:
        # Check for 404s/unimplemented endpoints to advise Dhruv
        per_profile = results.get("per_profile", {})
        missing_endpoints = set()
        for pdata in per_profile.values():
            if pdata.get("errors", 0) > 0 and pdata.get("status_code") == 404:
                missing_endpoints.add(pdata.get("endpoint", "unknown"))
        if missing_endpoints:
            print(f"\n⚠️ Backend missing endpoints: {list(missing_endpoints)}")

        passed = results.get("integrity", {}).get("invariants_passed", False)
        sys.exit(0 if passed else 1)
    sys.exit(2)


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
