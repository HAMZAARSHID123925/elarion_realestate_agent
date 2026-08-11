"""
Human Escalation Node — Phase 5, Workflow #4.

Creates a durable escalation record in PostgreSQL, alerts the assigned property manager,
and halts automated progression at PENDING_MANAGER_ACTION until an authorized manager action is received.
"""
import logging
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState
from app.core_workflows.rent_renewal.human_escalation.service import trigger_human_escalation

logger = logging.getLogger(__name__)


async def human_escalation_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: human_escalation_node
    Creates human escalation record and records manager notification.
    """
    logs = state.get("logs", [])
    tenant_id = state.get("tenant_id", "T-UNKNOWN")
    lease_id = state.get("lease_id", "L-UNKNOWN")

    esc_result = await trigger_human_escalation(state)
    esc_id = esc_result.get("escalation_id")
    reason = esc_result.get("escalation_reason") or "RENEWAL_APPROVAL_REQUIRED"

    logs.append(
        f"[human_escalation_node] Case escalated to Property Manager for lease {lease_id} "
        f"(escalation_id={esc_id}, reason={reason})"
    )

    return {
        "escalation_id": esc_id,
        "escalation_required": True,
        "escalation_status": "PENDING_MANAGER_ACTION",
        "renewal_status": "ESCALATED",
        "notification_status": "manager_alerted",
        "logs": logs,
    }
