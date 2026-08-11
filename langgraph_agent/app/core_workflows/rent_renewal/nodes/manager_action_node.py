"""
Manager Action Node — Phase 5, Workflow #4.

Processes authorized property manager decisions on escalations,
updating the escalation lifecycle and routing the workflow to resume or close.
"""
import logging
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState
from app.core_workflows.rent_renewal.human_escalation.service import process_manager_decision

logger = logging.getLogger(__name__)


async def manager_action_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: manager_action_node
    Processes manager action input from state.
    """
    logs = state.get("logs", [])
    escalation_id = state.get("escalation_id")
    action = state.get("manager_action") or "APPROVE_CONTINUATION"
    notes = state.get("manager_notes") or ""
    actor = state.get("manager_id") or "Property Manager"

    if escalation_id:
        try:
            decision_res = await process_manager_decision(
                escalation_id=escalation_id,
                action=action,
                notes=notes,
                actor=actor,
            )
            next_status = decision_res["next_renewal_status"]
            esc_status = decision_res["escalation_status"]
        except Exception as e:
            logger.error("Error applying manager decision: %s", e)
            next_status = "RENEWAL_IN_PROGRESS" if action == "APPROVE_CONTINUATION" else "CLOSED"
            esc_status = "RESOLVED"
    else:
        # Direct state decision without DB escalation ID
        if action == "APPROVE_CONTINUATION":
            next_status = "RENEWAL_IN_PROGRESS"
            esc_status = "RESOLVED"
        elif action in ("REJECT_CONTINUATION", "CLOSE_CASE"):
            next_status = "TENANT_DECLINED"
            esc_status = "CLOSED"
        elif action == "REQUEST_MORE_INFORMATION":
            next_status = "CLARIFICATION_REQUIRED"
            esc_status = "PENDING_MANAGER_ACTION"
        else:
            next_status = "PENDING_MANAGER_REVIEW"
            esc_status = "OPEN"

    logs.append(
        f"[manager_action_node] Manager action '{action}' processed. "
        f"Renewal status -> '{next_status}', escalation -> '{esc_status}'"
    )

    return {
        "manager_action": action,
        "manager_notes": notes,
        "escalation_status": esc_status,
        "renewal_status": next_status,
        "logs": logs,
    }
