"""
Manager Notification Service — Phase 3, Workflow #4.

Alerts property managers when a tenant states renewal intent (YES) or requests negotiation.
Enforces the strict Human-in-the-Loop boundary:
    Tenant Intent != Renewal Approval.
All positive intents require human authorization before renewal is approved.
"""
import os
import logging
from typing import Dict, Any, Optional

from app.core_workflows.rent_renewal.renewal_intent import repository

logger = logging.getLogger(__name__)


async def notify_manager_of_renewal_intent(
    lease_id: str,
    tenant_id: str,
    tenant_name: str,
    property_id: str,
    property_address: str,
    intent: str,
    tenant_response: str,
    current_rent: float = 0.0,
    lease_end_date: str = "",
    requested_term: Optional[int] = None,
    proposed_rent: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Creates and records a manager review notification task.

    Args:
        lease_id: Unique lease identifier.
        tenant_id: Tenant identifier.
        tenant_name: Resident name.
        property_id: Property identifier.
        property_address: Property address.
        intent: 'YES' or 'NEGOTIATION'
        tenant_response: Verbatim tenant response message.
        current_rent: Current monthly rent in PKR.
        lease_end_date: Lease end date string.
        requested_term: Optional requested renewal duration in months.
        proposed_rent: Optional counter-offered rent amount.

    Returns:
        Dict containing notification_id, status, and alert summary.
    """
    if intent == "NEGOTIATION":
        notif_type = "RENEWAL_NEGOTIATION"
        title = f"Renewal Negotiation Request — {tenant_name} ({property_address})"
        action_required = "Review tenant counter-offer/terms and formulate renewal offer."
    else:
        notif_type = "RENEWAL_INTENT_YES"
        title = f"Tenant Confirmed Renewal Intent — Review Required: {tenant_name} ({property_address})"
        action_required = "Review tenant history and authorize updated lease agreement."

    details = {
        "tenant_name": tenant_name,
        "property_address": property_address,
        "current_monthly_rent": current_rent,
        "lease_end_date": lease_end_date,
        "tenant_verbatim_response": tenant_response,
        "intent_classified": intent,
        "requested_term_months": requested_term,
        "proposed_rent": proposed_rent,
        "action_required": action_required,
        "human_decision_pending": True,
    }

    notification_id = await repository.create_manager_notification(
        notification_type=notif_type,
        lease_id=lease_id,
        tenant_id=tenant_id,
        property_id=property_id,
        title=title,
        details=details,
    )

    logger.info(
        "[HITL Alert] Manager review task created (#%d) for lease %s. Decision required by human authority.",
        notification_id, lease_id
    )

    return {
        "notification_id": notification_id,
        "notification_type": notif_type,
        "title": title,
        "status": "MANAGER_ALERTED",
        "details": details,
    }
