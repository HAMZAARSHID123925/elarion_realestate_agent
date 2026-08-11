"""
Renewal Reminder Scheduler Entry Point — Phase 2, Workflow #4.

CLI / cron entry point for dispatching renewal reminder messages.
Mirrors the lease_expiry/scheduler_entry.py and rent_reminder/scheduler.py patterns.

Usage:
    cd langgraph_agent
    python -m app.core_workflows.rent_renewal.renewal_reminder.scheduler_entry
"""
import sys
import os
import asyncio
import logging
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from dotenv import load_dotenv
load_dotenv()

from app.core_workflows.rent_renewal.renewal_reminder.service import run_renewal_reminder_dispatch

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    summary = asyncio.run(run_renewal_reminder_dispatch())
    print(json.dumps(summary, indent=2, default=str))

    if summary.get("status") == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    main()
