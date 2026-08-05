"""
Daily Scheduler & Batch Runner for Rent Reminder & Escalation Workflows.
Implements Section 4 & 5 of the PDF Blueprint.
"""
import logging
import sys
import os
from datetime import date
from typing import Dict, Any, List

# Ensure workspace root is in sys.path so 'database' can be imported from any CWD
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))


from app.core_workflows.rent_reminder.graph import rent_reminder_graph
from database.rent_models import get_unpaid_overdue_tenants, seed_sample_tenants

logger = logging.getLogger(__name__)


def run_daily_rent_reminder_workflow(current_date_str: str = None) -> Dict[str, Any]:
    """
    Executes the daily automated scan for overdue rent records.
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Seeding sample tenant data...")
    seed_sample_tenants()
    print("Executing daily workflow run...")
    results = run_daily_rent_reminder_workflow(current_date_str="2026-08-05")
    print(f"Results Summary: {results}")
