"""
Human Escalation Detection Engine — Phase 5, Workflow #4.

Pure deterministic logic for evaluating workflow state to determine
if human escalation is required, classifying the escalation reason,
and assigning priority.
No DB, no LLM, no side effects. Fully unit-testable.
"""
import re
from typing import Dict, Any, Tuple, Optional
from app.core_workflows.rent_renewal.human_escalation.config import ESCALATION_REASONS


def detect_escalation_requirement(state: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Evaluates workflow state to determine if human escalation is triggered.

    Returns:
        Tuple of:
          - is_required (bool)
          - reason (str, e.g. 'RENEWAL_APPROVAL_REQUIRED', 'NEGOTIATION_REQUIRED', etc.)
          - priority (str, e.g. 'LOW', 'MEDIUM', 'HIGH', 'URGENT')
          - description (str)
    """
    # 1. Explicit escalation flag already in state
    if state.get("escalation_required") is True:
        reason = state.get("escalation_reason") or "OTHER"
        priority = state.get("escalation_priority") or ESCALATION_REASONS.get(reason, {}).get("default_priority", "MEDIUM")
        desc = state.get("escalation_description") or f"Explicit escalation requested: {reason}"
        return True, reason, priority, desc

    renewal_intent = state.get("renewal_intent")
    tenant_response = (state.get("tenant_response") or "").lower()
    renewal_status = state.get("renewal_status")
    document_status = state.get("document_status")

    # 2. Check for explicit tenant request to speak with a human / manager
    human_request_patterns = [
        r"\bcall me\b", r"\bspeak to\b", r"\bhuman\b", r"\bmanager\b",
        r"\btalk to a person\b", r"\bcontact me directly\b", r"\brepresentative\b"
    ]
    for pattern in human_request_patterns:
        if re.search(pattern, tenant_response):
            return (
                True,
                "TENANT_REQUESTED_HUMAN",
                "MEDIUM",
                f"Tenant explicitly requested human property manager contact (matched '{pattern}')."
            )

    # 3. Check for negotiation / terms bargaining
    if renewal_intent == "NEGOTIATION":
        return (
            True,
            "NEGOTIATION_REQUIRED",
            "HIGH",
            "Tenant requested lease term negotiation or rent reduction."
        )

    # 4. Check for positive renewal intent (requires manager approval: HITL rule)
    if renewal_intent == "YES" or renewal_status == "PENDING_MANAGER_REVIEW":
        return (
            True,
            "RENEWAL_APPROVAL_REQUIRED",
            "MEDIUM",
            "Tenant confirmed renewal intent. Human manager review required to authorize agreement."
        )

    # 5. Check for document verification problems
    if document_status == "REJECTED" or state.get("document_exception") is True:
        return (
            True,
            "DOCUMENT_ISSUE",
            "MEDIUM",
            "Document submission was rejected or encountered an unresolved exception."
        )

    # 6. Check for operational workflow errors
    if state.get("workflow_error"):
        return (
            True,
            "WORKFLOW_ERROR",
            "HIGH",
            f"Operational error occurred: {state.get('workflow_error')}"
        )

    return False, None, None, None
