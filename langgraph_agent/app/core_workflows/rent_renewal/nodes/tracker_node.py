"""
Renewal Tracker Node — Workflow #4.
Finalizes the renewal workflow cycle, records audit history, and manages state termination.
"""
import logging
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState

logger = logging.getLogger(__name__)


def renewal_tracker_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: renewal_tracker_node
    Finalizes cycle and audits workflow state.
    """
    logs = state.get("logs", [])
    tenant_id = state.get("tenant_id", "T-UNKNOWN")
    status = state.get("renewal_status", "UNKNOWN")

    # Workflow is complete for single-turn actions (reminders sent, manager alerted, declined)
    # or awaiting tenant response if clarification was requested
    is_complete = status != "CLARIFICATION_REQUIRED"

    logs.append(
        f"[renewal_tracker_node] Audited renewal state for tenant {tenant_id}: "
        f"status='{status}', is_complete={is_complete}"
    )

    return {
        "is_complete": is_complete,
        "logs": logs,
    }
