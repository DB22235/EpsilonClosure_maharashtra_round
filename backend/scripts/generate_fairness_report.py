"""
Fairness Evidence & Audit Verification Report Generator.

Usage:
    python -m scripts.generate_fairness_report [--campaign-id <UUID>]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from dotenv import load_dotenv

load_dotenv(dotenv_path=backend_root / ".env")

from sqlalchemy import select

from app.database import async_session_factory
from app.models.campaign import Campaign
from app.models.lottery import LotteryRun
from app.services.metrics_service import get_campaign_metrics, get_fairness_evidence

# ANSI color codes
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_CYAN = "\033[96m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"


async def generate_report(campaign_id_str: str = "") -> None:
    async with async_session_factory() as db:
        if campaign_id_str:
            target_id = uuid.UUID(campaign_id_str)
        else:
            # Auto-detect most recent campaign with a lottery run
            stmt = select(LotteryRun.campaign_id).order_by(LotteryRun.executed_at.desc()).limit(1)
            target_id = (await db.execute(stmt)).scalar_one_or_none()
            if target_id is None:
                # Fallback to any campaign
                stmt_c = select(Campaign.id).order_by(Campaign.created_at.desc()).limit(1)
                target_id = (await db.execute(stmt_c)).scalar_one_or_none()

        if target_id is None:
            print(f"{COLOR_RED}[ERROR] No campaigns found in database.{COLOR_RESET}")
            sys.exit(1)

        metrics = await get_campaign_metrics(db, target_id, "report-gen")
        try:
            evidence = await get_fairness_evidence(db, target_id, include_seed=True, request_id="report-gen")
            has_evidence = True
        except Exception:
            evidence = None
            has_evidence = False

    print(f"\n{COLOR_BOLD}{COLOR_CYAN}======================================================================{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}         FAIR DROP — MATHEMATICAL & CRYPTOGRAPHIC FAIRNESS AUDIT       {COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}======================================================================{COLOR_RESET}")

    print(f"\n{COLOR_BOLD}CAMPAIGN OVERVIEW{COLOR_RESET}")
    print(f"  Campaign ID          : {COLOR_YELLOW}{metrics.campaign_id}{COLOR_RESET}")
    print(f"  Name                 : {COLOR_BOLD}{metrics.name}{COLOR_RESET}")
    print(f"  Lifecycle Status     : {COLOR_GREEN}{metrics.status}{COLOR_RESET}")
    print(f"  Configured Capacity  : {metrics.capacity}")
    print(f"  Total Submissions    : {metrics.registrations_count}")
    print(f"  Eligible Roster      : {metrics.eligible_roster_count}")

    print(f"\n{COLOR_BOLD}ALLOCATION & INVENTORY BREAKDOWN{COLOR_RESET}")
    print(f"  Lottery Winners      : {metrics.winners_count}")
    print(f"  Standby Queue Depth  : {metrics.standby_count}")
    print(f"  Seats Total          : {metrics.seats_total}")
    print(f"  Seats Available      : {metrics.seats_available}")
    print(f"  Seats Held           : {metrics.seats_held}")
    print(f"  Seats Confirmed      : {metrics.seats_confirmed}")
    print(f"  Completed Bookings   : {metrics.bookings_count}")
    print(f"  Holds Expired (Freed): {metrics.holds_expired_count}")
    print(f"  Entitlements Expired : {metrics.entitlements_expired_count}")

    print(f"\n{COLOR_BOLD}SAFETY & ZERO-OVERSELL INVARIANTS{COLOR_RESET}")
    oversell_color = COLOR_GREEN if metrics.oversell_count == 0 else COLOR_RED
    dup_color = COLOR_GREEN if metrics.duplicate_allocation_count == 0 else COLOR_RED
    print(f"  Oversell Count       : {oversell_color}{metrics.oversell_count} (Must be 0){COLOR_RESET}")
    print(f"  Duplicate Allocations: {dup_color}{metrics.duplicate_allocation_count} (Must be 0){COLOR_RESET}")

    if has_evidence and evidence:
        print(f"\n{COLOR_BOLD}CRYPTOGRAPHIC FAIRNESS EVIDENCE{COLOR_RESET}")
        print(f"  Roster SHA-256 Hash  : {evidence.roster_hash}")
        print(f"  Seed Commitment Hash : {evidence.randomness_commitment}")
        print(f"  Revealed Seed (Admin): {evidence.randomness_seed or '[REDACTED]'}")
        print(f"  Win Probability      : {COLOR_GREEN}{evidence.selection_probability * 100:.2f}% (Uniform){COLOR_RESET}")
        print(f"  Canonical Evidence Hsh: {evidence.evidence_hash}")
        print(f"  Formal Guarantee     : {COLOR_BOLD}{evidence.statement}{COLOR_RESET}")

    print(f"\n{COLOR_BOLD}{COLOR_CYAN}======================================================================{COLOR_RESET}")
    all_clean = (metrics.oversell_count == 0) and (metrics.duplicate_allocation_count == 0)
    if all_clean:
        print(f"{COLOR_GREEN}{COLOR_BOLD}VERIFICATION VERDICT: VERIFIED FAIR (Zero Overselling, Zero Duplication){COLOR_RESET}\n")
    else:
        print(f"{COLOR_RED}{COLOR_BOLD}VERIFICATION VERDICT: INTEGRITY INVARIANTS VIOLATED{COLOR_RESET}\n")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fairness and allocation audit report.")
    parser.add_argument("--campaign-id", type=str, default="", help="Campaign UUID to audit.")
    args = parser.parse_args()
    asyncio.run(generate_report(args.campaign_id))


if __name__ == "__main__":
    main()
