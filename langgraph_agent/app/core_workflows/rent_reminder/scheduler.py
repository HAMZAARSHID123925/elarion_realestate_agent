"""
Daily Scheduler & Batch Runner for Rent Reminder & Escalation Workflows.
Implements automated morning scheduling, 30-day billing cycle checks based on joining date, 31-35 day warnings, and Day 36 direct human transfer.
"""
import logging
import sys
import os
import asyncio
from datetime import date, datetime, time
from typing import Dict, Any, List, Optional

# Ensure workspace root is in sys.path so 'database' can be imported from any CWD
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from app.core_workflows.rent_reminder.graph import rent_reminder_graph
from database.rent_models import get_unpaid_overdue_tenants, seed_sample_tenants

logger = logging.getLogger(__name__)


def run_daily_rent_reminder_workflow(current_date_str: str = None) -> Dict[str, Any]:
    """
    Executes the daily automated scan for overdue rent records based on joining dates & 30-day cycles.
    Iterates through candidates and runs the rent_reminder_graph for each.
    """
    if not current_date_str:
        current_date_str = date.today().isoformat()

    logger.info(f"--- Starting Daily Rent Reminder Scan for Date: {current_date_str} ---")

    candidates = get_unpaid_overdue_tenants(ref_date_str=current_date_str)
    
    summary = {
        "run_date": current_date_str,
        "records_scanned": len(candidates),
        "reminders_sent": 0,
        "followups_sent": 0,
        "escalated": 0,
        "skipped": 0,
        "details": []
    }

    for candidate in candidates:
        initial_state = {
            "tenant_id": candidate["tenant_id"],
            "tenant_name": candidate["tenant_name"],
            "tenant_phone": candidate["tenant_phone"],
            "property_address": candidate["property_address"],
            "joining_date": candidate.get("joining_date"),
            "rent_amount": candidate["rent_amount"],
            "rent_due_date": candidate["rent_due_date"],
            "reminder_30_sent_at": candidate["reminder_30_sent_at"],
            "reminder_5_sent_at": candidate["reminder_5_sent_at"],
            "response_received": bool(candidate["response_received"]),
            "human_escalated": bool(candidate["human_escalated"]),
            "escalation_reason": candidate["escalation_reason"],
            "manual_hold": bool(candidate["manual_hold"]),
            "payment_status": candidate["payment_status"],
            "last_reminder_status": candidate["last_reminder_status"],
            "current_date": current_date_str,
            "logs": []
        }

        # Run LangGraph subgraph for candidate
        final_state = rent_reminder_graph.invoke(initial_state)
        action = final_state.get("action")

        if action == "SEND_REMINDER":
            summary["reminders_sent"] += 1
        elif action == "SEND_FOLLOWUP":
            summary["followups_sent"] += 1
        elif action == "ESCALATE":
            summary["escalated"] += 1
        else:
            summary["skipped"] += 1

        summary["details"].append({
            "tenant_id": candidate["tenant_id"],
            "tenant_name": candidate["tenant_name"],
            "action": action,
            "logs": final_state.get("logs", [])
        })

    logger.info(
        f"--- Daily Scan Completed: Scanned {summary['records_scanned']}, "
        f"Reminders Sent {summary['reminders_sent']}, Followups Sent {summary['followups_sent']}, "
        f"Escalated {summary['escalated']}, Skipped {summary['skipped']} ---"
    )

    return summary


class AutomatedRentScheduler:
    """
    Production-Ready Asynchronous Scheduler Engine for Daily Morning Rent Checks.
    Runs every morning at a configurable target time (e.g. 08:00 AM) or interval.
    """
    def __init__(self, run_hour: int = 8, run_minute: int = 0, interval_seconds: Optional[int] = None):
        self.run_hour = run_hour
        self.run_minute = run_minute
        self.interval_seconds = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def _scheduler_loop(self):
        logger.info(f"[AutomatedRentScheduler] Started background scheduler loop (Target morning time: {self.run_hour:02d}:{self.run_minute:02d} AM).")
        while self._running:
            try:
                if self.interval_seconds:
                    await asyncio.sleep(self.interval_seconds)
                else:
                    # Calculate seconds until next target morning time
                    now = datetime.now()
                    target_today = datetime.combine(now.date(), time(self.run_hour, self.run_minute))
                    if now >= target_today:
                        # Target time already passed today, schedule for tomorrow
                        target_next = target_today.replace(day=now.day + 1)
                    else:
                        target_next = target_today
                    
                    delay = (target_next - now).total_seconds()
                    logger.info(f"[AutomatedRentScheduler] Sleeping for {delay:.1f} seconds until next scheduled run at {target_next}.")
                    await asyncio.sleep(delay)

                if self._running:
                    logger.info("[AutomatedRentScheduler] Triggering morning rent reminder batch workflow execution...")
                    summary = run_daily_rent_reminder_workflow()
                    logger.info(f"[AutomatedRentScheduler] Morning run summary: {summary}")

            except asyncio.CancelledError:
                logger.info("[AutomatedRentScheduler] Scheduler loop cancelled.")
                break
            except Exception as e:
                logger.exception(f"[AutomatedRentScheduler] Error during scheduled execution: {e}")
                # Wait 60 seconds before retrying on failure to avoid rapid retry loops
                await asyncio.sleep(60)

    def start(self):
        """Starts the background scheduler task."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._scheduler_loop())
            logger.info("[AutomatedRentScheduler] Background scheduler task initialized.")

    async def stop(self):
        """Gracefully stops the background scheduler task."""
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            logger.info("[AutomatedRentScheduler] Scheduler stopped cleanly.")


# Global singleton instance for app lifespan integration
rent_scheduler = AutomatedRentScheduler(run_hour=8, run_minute=0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Seeding sample tenant data...")
    seed_sample_tenants()
    print("Executing daily workflow run...")
    results = run_daily_rent_reminder_workflow(current_date_str="2026-08-05")
    print(f"Results Summary: {results}")

