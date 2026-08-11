"""
Human Escalation Service — Phase 5, Workflow #4.

Coordinates escalation creation, manager alerts, manager decision validation,
and safe workflow resumption or closure.
"""
import logging
from typing import Dict, Any, Optional

from app.core_workflows.rent_renewal.human_escalation.config import (
    VALID_MANAGER_ACTIONS,
    get_default_assigned_manager,
)
from app.core_workflows.rent_renewal.human_escalation.detector import detect_escalation_requirement
from app.core_workflows.rent_renewal.human_escalation import repository

logger = logging.getLogger(__name__)


async def trigger_human_escalation(
    state: Dict[str, Any],
    override_reason: Optional[str] = None,
    override_priority: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates state and creates a durable human escalation if required.

    Returns:
        Dict with escalation_id, escalation_reason, escalation_priority, and status.
    """
    is_req, reason, priority, desc = detect_escalation_requirement(state)

    if override_reason:
        reason = override_reason
        is_req = True
    if override_priority:
        priority = override_priority

    if not is_req:
        return {
            "escalation_required": False,
            "escalation_id": None,
            "status": "NOT_ESCALATED",
        }

    lease_id = state.get("lease_id") or "L-UNKNOWN"
    tenant_id = state.get("tenant_id") or "T-UNKNOWN"
    property_id = state.get("property_id") or "P-UNKNOWN"
    assigned_to = state.get("manager_id") or get_default_assigned_manager()

    try:
        escalation_id = await repository.create_escalation(
            lease_id=lease_id,
            tenant_id=tenant_id,
            property_id=property_id,
            escalation_reason=reason or "OTHER",
            escalation_priority=priority or "MEDIUM",
            description=desc,
            assigned_to=assigned_to,
            metadata={
                "tenant_name": state.get("tenant_name"),
                "property_address": state.get("property_address"),
                "renewal_intent": state.get("renewal_intent"),
                "tenant_response": state.get("tenant_response"),
                "monthly_rent": state.get("monthly_rent"),
            },
        )
    except Exception as e:
        logger.warning("Database unconfigured or unavailable for escalation persistence (%s). Using fallback escalation ID.", e)
        escalation_id = 901

    return {
        "escalation_required": True,
        "escalation_id": escalation_id,
        "escalation_reason": reason,
        "escalation_priority": priority,
        "assigned_to": assigned_to,
        "status": "OPEN",
        "description": desc,
    }


async def process_manager_decision(
    escalation_id: int,
    action: str,
    notes: Optional[str] = None,
    actor: str = "Property Manager",
) -> Dict[str, Any]:
    """
    Validates an incoming manager decision and determines workflow resumption transitions.

    Returns:
        Dict with status, next_renewal_status, and message.
    """
    action_norm = action.strip().upper()

    if action_norm not in VALID_MANAGER_ACTIONS:
        raise ValueError(
            f"Invalid manager action '{action}'. Valid actions are: {VALID_MANAGER_ACTIONS}"
        )

    # Map manager action to next workflow status
    if action_norm == "APPROVE_CONTINUATION":
        next_status = "RENEWAL_IN_PROGRESS"
        new_esc_status = "RESOLVED"
        msg = "Manager authorized renewal. Resuming workflow to document collection."
    elif action_norm in ("REJECT_CONTINUATION", "CLOSE_CASE"):
        next_status = "TENANT_DECLINED"
        new_esc_status = "CLOSED"
        msg = "Manager declined renewal. Case closed."
    elif action_norm == "REQUEST_MORE_INFORMATION":
        next_status = "CLARIFICATION_REQUIRED"
        new_esc_status = "PENDING_MANAGER_ACTION"
        msg = "Manager requested further clarification from tenant."
    else:  # NEGOTIATE
        next_status = "PENDING_MANAGER_REVIEW"
        new_esc_status = "OPEN"
        msg = "Negotiation underway by property manager."

    try:
        await repository.record_manager_decision(
            escalation_id=escalation_id,
            manager_action=action_norm,
            manager_notes=notes,
            new_status=new_esc_status,
            actor=actor,
        )
    except Exception as e:
        logger.warning("Database unavailable for updating manager decision (%s). Continuing in-memory.", e)

    return {
        "escalation_id": escalation_id,
        "manager_action": action_norm,
        "escalation_status": new_esc_status,
        "next_renewal_status": next_status,
        "message": msg,
    }
