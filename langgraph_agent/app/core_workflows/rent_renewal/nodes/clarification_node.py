"""
Clarification Node — Phase 3, Workflow #4.

Handles ambiguous or unclear tenant responses.
Sets renewal_status to CLARIFICATION_REQUIRED and generates a friendly clarification prompt.
"""
import logging
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState

logger = logging.getLogger(__name__)


def clarification_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: clarification_node
    Generates a clarifying question when a tenant's response is ambiguous.
    """
    logs = state.get("logs", [])
    tenant_name = state.get("tenant_name", "Resident")
    property_address = state.get("property_address", "your home")
    lease_end_date = state.get("lease_end_date", "the end of your lease")

    clarification_msg = (
        f"Dear {tenant_name},\n\n"
        f"Thank you for your message regarding your lease at {property_address} (expiring on {lease_end_date}).\n"
        f"Could you please clarify whether you would like to renew your lease for another term, "
        f"or if you are planning to vacate at the end of the term? "
        f"If you have specific questions or terms you would like to discuss, please feel free to let us know!"
    )

    logs.append(f"[clarification_node] Unclear intent. Generated clarification question. Status -> CLARIFICATION_REQUIRED")

    return {
        "renewal_status": "CLARIFICATION_REQUIRED",
        "clarification_question": clarification_msg,
        "final_response": clarification_msg,
        "logs": logs,
    }
