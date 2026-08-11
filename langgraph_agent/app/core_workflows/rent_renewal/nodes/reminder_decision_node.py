"""
Reminder Decision Node — Workflow #4.
Pure rule engine deciding whether to send a renewal reminder or skip.
"""
import logging
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState

logger = logging.getLogger(__name__)


def renewal_reminder_decision_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: renewal_reminder_decision_node
    Decides action: SEND_REMINDER | SKIP
    """
    logs = state.get("logs", [])
    expiry_stage = state.get("expiry_stage", "90_DAYS")
    last_reminder_type = state.get("last_reminder_type")

    expected_reminder_type = f"LEASE_EXPIRY_{expiry_stage}" if expiry_stage != "EXPIRED" else "LEASE_EXPIRED"

    if expiry_stage == "FUTURE":
        action = "SKIP"
        logs.append("[reminder_decision] Lease not within renewal window (>90 days). Action: SKIP")
    elif last_reminder_type == expected_reminder_type:
        action = "SKIP"
        logs.append(f"[reminder_decision] Reminder already sent for {expected_reminder_type}. Action: SKIP")
    else:
        action = "SEND_REMINDER"
        logs.append(f"[reminder_decision] Triggering reminder for {expected_reminder_type}. Action: SEND_REMINDER")

    return {
        "action": action,
        "logs": logs,
    }
