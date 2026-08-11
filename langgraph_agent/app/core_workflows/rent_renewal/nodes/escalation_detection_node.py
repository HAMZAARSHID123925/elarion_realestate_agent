"""
Escalation Detection Node — Phase 5, Workflow #4.

Evaluates workflow state to determine whether human manager escalation is required,
categorizing the reason and setting the priority level.
"""
import logging
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState
from app.core_workflows.rent_renewal.human_escalation.detector import detect_escalation_requirement

logger = logging.getLogger(__name__)


def escalation_detection_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: escalation_detection_node
    Evaluates state for escalation triggers.
    """
    logs = state.get("logs", [])
    tenant_id = state.get("tenant_id", "T-UNKNOWN")

    is_req, reason, priority, desc = detect_escalation_requirement(state)

    if is_req:
        logs.append(
            f"[escalation_detection_node] Escalation required for tenant {tenant_id}: "
            f"reason='{reason}', priority='{priority}'"
        )
    else:
        logs.append(f"[escalation_detection_node] No escalation required for tenant {tenant_id}.")

    return {
        "escalation_required": is_req,
        "escalation_reason": reason,
        "escalation_priority": priority,
        "logs": logs,
    }
