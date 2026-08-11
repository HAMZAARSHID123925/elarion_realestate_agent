"""
Scheduler Entry Point — Phase 1, Workflow #4.

CLI/cron entry point for the lease expiry scan.
Mirrors the rent_reminder/scheduler.py pattern.

Usage:
    cd langgraph_agent
    python -m app.core_workflows.rent_renewal.lease_expiry.scheduler_entry

For scheduled execution (cron/systemd timer):
    python -m app.core_workflows.rent_renewal.lease_expiry.scheduler_entry --trigger scheduled
"""
import sys
import os
import asyncio
import argparse
import logging
import json

# Ensure workspace root is in sys.path so imports work from any CWD
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from dotenv import load_dotenv
load_dotenv()

from app.core_workflows.rent_renewal.lease_expiry.service import run_expiry_scan

logger = logging.getLogger(__name__)


async def run_lease_expiry_scan(trigger_type: str = "manual") -> dict:
    """
    Public entry point for the lease expiry scan.

    Can be called from cron, systemd timer, Celery, or any scheduler.

    Args:
        trigger_type: 'manual' or 'scheduled'

    Returns:
        Summary dict with scan results.
    """
    logger.info("--- Starting Lease Expiry Scan (trigger: %s) ---", trigger_type)

    try:
        summary = await run_expiry_scan(trigger_type=trigger_type)
    except Exception as e:
        logger.error("Lease expiry scan failed: %s", e, exc_info=True)
        return {
            "status": "FAILED",
            "error": str(e),
        }

    logger.info(
        "--- Lease Expiry Scan Complete: scanned=%d created=%d dupes=%d errors=%d ---",
        summary.get("leases_scanned", 0),
        summary.get("events_created", 0),
        summary.get("duplicates_skipped", 0),
        summary.get("errors_count", 0),
    )

    return summary


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run the lease expiry tracking scan"
    )
    parser.add_argument(
        "--trigger",
        choices=["manual", "scheduled"],
        default="manual",
        help="Trigger type for observability (default: manual)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    summary = asyncio.run(run_lease_expiry_scan(trigger_type=args.trigger))
    print(json.dumps(summary, indent=2, default=str))

    # Exit with error code if scan had errors
    if summary.get("status") == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    main()
