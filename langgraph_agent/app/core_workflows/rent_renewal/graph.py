"""
Rent Renewal Workflow LangGraph Subgraph — Workflow #4.
Implements the Complete 5-Phase End-to-End LangGraph Architecture (SDD Master Blueprint).
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END

from app.core_workflows.rent_renewal.state import RentRenewalState
from app.core_workflows.rent_renewal.nodes import (
    lease_check_node,
    renewal_reminder_decision_node,
    renewal_reminder_send_node,
    intent_classification_node,
    manager_notification_node,
    decline_node,
    clarification_node,
    document_check_node,
    document_request_node,
    document_verification_node,
    escalation_detection_node,
    human_escalation_node,
    manager_action_node,
    renewal_tracker_node,
)


def route_entry_path(state: RentRenewalState) -> str:
    """
    Routes initial entry:
      - Manager action processing / resumption (Phase 5).
      - Explicit human escalation path (Phase 5).
      - Document checking path if renewal is in document collection stage (Phase 4).
      - Conversational intent path if tenant message exists (Phase 3).
      - Proactive reminder path for date scans (Phase 1 & 2).
    """
    action = state.get("action")
    manager_action = state.get("manager_action")
    renewal_status = state.get("renewal_status")
    escalation_required = state.get("escalation_required")

    if action == "APPLY_MANAGER_ACTION" or (manager_action and action != "CHECK_DOCUMENTS"):
        return "manager_action"

    if action == "ESCALATE" or (escalation_required and action != "CHECK_DOCUMENTS"):
        return "human_escalation"

    if action == "CHECK_DOCUMENTS" or renewal_status in ("RENEWAL_IN_PROGRESS", "DOCUMENTS_PENDING", "DOCUMENTS_UNDER_REVIEW"):
        return "document_check"

    tenant_response = state.get("tenant_response")
    messages = state.get("messages", [])

    if tenant_response or (messages and len(messages) > 0):
        return "intent_classification"

    return "renewal_reminder_decision"


def route_reminder_decision(state: RentRenewalState) -> str:
    """Routes proactive reminder decision."""
    action = state.get("action", "SKIP")
    if action == "SEND_REMINDER":
        return "renewal_reminder_send"
    return "renewal_tracker"


def route_intent_decision(state: RentRenewalState) -> str:
    """
    Routes based on classified tenant renewal intent:
      - YES / NEGOTIATION -> manager_notification (HITL: creates review task)
      - NO -> decline
      - UNCLEAR -> clarification
    """
    intent = state.get("renewal_intent", "UNCLEAR")
    if intent in ("YES", "NEGOTIATION"):
        return "manager_notification"
    elif intent == "NO":
        return "decline"
    else:
        return "clarification"


def route_document_check_decision(state: RentRenewalState) -> str:
    """
    Routes based on document checklist completeness:
      - Missing documents -> document_request (prompts tenant for missing items)
      - All documents received -> document_verification
    """
    doc_status = state.get("document_status", "PENDING")
    if doc_status in ("PENDING", "PARTIALLY_SUBMITTED"):
        return "document_request"
    return "document_verification"


def route_manager_action_continuation(state: RentRenewalState) -> str:
    """
    Routes workflow continuation following an authorized manager decision:
      - APPROVE_CONTINUATION (RENEWAL_IN_PROGRESS) -> document_check (advances to Phase 4)
      - REQUEST_MORE_INFORMATION (CLARIFICATION_REQUIRED) -> clarification
      - Otherwise -> renewal_tracker (finalizes state)
    """
    renewal_status = state.get("renewal_status")
    if renewal_status == "RENEWAL_IN_PROGRESS":
        return "document_check"
    elif renewal_status == "CLARIFICATION_REQUIRED":
        return "clarification"
    return "renewal_tracker"


def build_rent_renewal_graph(checkpointer=None):
    """
    Builds and compiles the complete Rent Renewal LangGraph Subgraph (Phases 1–5).
    """
    builder = StateGraph(RentRenewalState)

    # 1. Register all nodes
    builder.add_node("lease_check", lease_check_node)
    builder.add_node("renewal_reminder_decision", renewal_reminder_decision_node)
    builder.add_node("renewal_reminder_send", renewal_reminder_send_node)
    builder.add_node("intent_classification", intent_classification_node)
    builder.add_node("manager_notification", manager_notification_node)
    builder.add_node("decline", decline_node)
    builder.add_node("clarification", clarification_node)
    builder.add_node("document_check", document_check_node)
    builder.add_node("document_request", document_request_node)
    builder.add_node("document_verification", document_verification_node)
    builder.add_node("escalation_detection", escalation_detection_node)
    builder.add_node("human_escalation", human_escalation_node)
    builder.add_node("manager_action", manager_action_node)
    builder.add_node("renewal_tracker", renewal_tracker_node)

    # 2. Linear entry edge
    builder.add_edge(START, "lease_check")

    # 3. Conditional dispatch from lease_check
    builder.add_conditional_edges(
        "lease_check",
        route_entry_path,
        {
            "manager_action": "manager_action",
            "human_escalation": "human_escalation",
            "document_check": "document_check",
            "intent_classification": "intent_classification",
            "renewal_reminder_decision": "renewal_reminder_decision",
        }
    )

    # 4. Proactive Reminder branch (Phases 1 & 2)
    builder.add_conditional_edges(
        "renewal_reminder_decision",
        route_reminder_decision,
        {
            "renewal_reminder_send": "renewal_reminder_send",
            "renewal_tracker": "renewal_tracker",
        }
    )
    builder.add_edge("renewal_reminder_send", "renewal_tracker")

    # 5. Intent branch (Phase 3 & 5)
    builder.add_conditional_edges(
        "intent_classification",
        route_intent_decision,
        {
            "manager_notification": "manager_notification",
            "decline": "decline",
            "clarification": "clarification",
        }
    )
    builder.add_edge("manager_notification", "renewal_tracker")
    builder.add_edge("human_escalation", "renewal_tracker")
    builder.add_edge("decline", "renewal_tracker")
    builder.add_edge("clarification", "renewal_tracker")

    # 6. Document Tracking branch (Phase 4)
    builder.add_conditional_edges(
        "document_check",
        route_document_check_decision,
        {
            "document_request": "document_request",
            "document_verification": "document_verification",
        }
    )
    builder.add_edge("document_request", "renewal_tracker")
    builder.add_edge("document_verification", "renewal_tracker")

    # 7. Manager Action & Resumption branch (Phase 5)
    builder.add_conditional_edges(
        "manager_action",
        route_manager_action_continuation,
        {
            "document_check": "document_check",
            "clarification": "clarification",
            "renewal_tracker": "renewal_tracker",
        }
    )

    # 8. Final completion edge
    builder.add_edge("renewal_tracker", END)

    return builder.compile(checkpointer=checkpointer)


rent_renewal_graph = build_rent_renewal_graph()
