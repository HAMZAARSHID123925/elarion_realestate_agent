"""
Decline Node — Phase 3, Workflow #4.

Handles tenant decline/non-renewal decisions.
Sets renewal_status to TENANT_DECLINED and prepares move-out coordination information.
"""
import logging
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState

logger = logging.getLogger(__name__)


def decline_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: decline_node
    Records tenant non-renewal decision and sets up move-out acknowledgement.
    """
    logs = state.get("logs", [])
    tenant_id = state.get("tenant_id", "T-UNKNOWN")
    property_address = state.get("property_address", "the property")
    lease_end_date = state.get("lease_end_date", "the end of your term")

    acknowledgement_msg = (
        f"We have received your confirmation that you do not plan to renew your lease for {property_address}. "
        f"Your tenancy will conclude on {lease_end_date}. "
        f"Our management team will follow up with standard move-out and key handover instructions. "
        f"Thank you for being a valued resident."
    )

    logs.append(f"[decline_node] Tenant {tenant_id} declined renewal. Status -> TENANT_DECLINED")

    return {
        "renewal_status": "TENANT_DECLINED",
        "tenant_decision": "declined",
        "final_response": acknowledgement_msg,
        "logs": logs,
    }
