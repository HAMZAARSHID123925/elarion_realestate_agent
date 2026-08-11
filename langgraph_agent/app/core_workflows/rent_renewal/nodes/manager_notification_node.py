"""
Manager Notification Node — Phase 3, Workflow #4.

Triggered when a tenant expresses positive renewal intent (YES) or requests negotiation.
Enforces the Human-in-the-Loop boundary:
    Tenant Intent != Renewal Approval.
Creates a formal manager review task in manager_notifications.
"""
import logging
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState
from app.core_workflows.rent_renewal.renewal_intent.notifications import notify_manager_of_renewal_intent

logger = logging.getLogger(__name__)


async def manager_notification_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: manager_notification_node
    Alerts the property manager and records the pending review task.
    """
    logs = state.get("logs", [])
    tenant_id = state.get("tenant_id", "T-UNKNOWN")
    lease_id = state.get("lease_id", "L-UNKNOWN")
    property_id = state.get("property_id", "P-UNKNOWN")
    tenant_name = state.get("tenant_name", "Resident")
    property_address = state.get("property_address", "Property Unit")
    intent = state.get("renewal_intent", "YES")
    tenant_response = state.get("tenant_response", "")
    current_rent = float(state.get("monthly_rent") or 0.0)
    lease_end_date = str(state.get("lease_end_date", ""))
    requested_term = state.get("requested_term_months")
    proposed_rent = state.get("proposed_rent")

    notification_id = None
    try:
        if lease_id and lease_id != "L-UNKNOWN":
            notif_res = await notify_manager_of_renewal_intent(
                lease_id=lease_id,
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                property_id=property_id,
                property_address=property_address,
                intent=intent,
                tenant_response=tenant_response,
                current_rent=current_rent,
                lease_end_date=lease_end_date,
                requested_term=requested_term,
                proposed_rent=proposed_rent,
            )
            notification_id = notif_res.get("notification_id")
    except Exception as e:
        logger.error("Error creating manager notification for lease %s: %s", lease_id, e)

    logs.append(
        f"[manager_notification_node] Manager notified for tenant {tenant_id} "
        f"(intent={intent}, notif_id={notification_id}). Status=PENDING_MANAGER_REVIEW"
    )

    return {
        "renewal_status": "PENDING_MANAGER_REVIEW",
        "manager_notification_id": notification_id,
        "manager_notification_status": "ALERTED",
        "notification_status": "manager_alerted",
        "logs": logs,
    }
