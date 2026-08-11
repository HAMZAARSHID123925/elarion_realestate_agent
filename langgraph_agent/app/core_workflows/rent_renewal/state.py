"""
Rent Renewal Workflow State Schema — Workflow #4.
Implements the full 5-tier state architecture defined in SDD Section 12 & Phases 1–5.
"""
from typing import TypedDict, Optional, List, Dict, Any


class RentRenewalState(TypedDict, total=False):
    # Core Identifiers
    tenant_id: Optional[str]
    property_id: Optional[str]
    lease_id: Optional[str]
    unit_id: Optional[str]

    # Lease Context
    tenant_name: Optional[str]
    tenant_contact: Optional[str]
    property_address: Optional[str]
    lease_start_date: Optional[str]
    lease_end_date: Optional[str]
    days_to_expiry: Optional[int]
    expiry_stage: Optional[str]  # "90_DAYS", "60_DAYS", "30_DAYS", "7_DAYS", "EXPIRED", "FUTURE"

    # Financials
    monthly_rent: Optional[float]
    offered_rent: Optional[float]
    proposed_rent: Optional[float]
    renewal_term_months: Optional[int]
    requested_term_months: Optional[int]

    # Renewal Lifecycle State Machine (SDD Section 13)
    # ACTIVE -> APPROACHING_EXPIRY -> REMINDER_SENT -> AWAITING_TENANT_RESPONSE
    # -> PENDING_MANAGER_REVIEW / TENANT_DECLINED / CLARIFICATION_REQUIRED / ESCALATED
    # -> RENEWAL_IN_PROGRESS -> DOCUMENTS_PENDING -> DOCUMENTS_UNDER_REVIEW -> COMPLETED
    renewal_status: Optional[str]
    renewal_intent: Optional[str]  # "YES" | "NO" | "UNCLEAR" | "NEGOTIATION"
    intent_confidence: Optional[float]
    intent_reasoning: Optional[str]
    tenant_response: Optional[str]
    tenant_decision: Optional[str]

    # Phase 2: Reminder & Communication State
    action: Optional[str]  # "SEND_REMINDER" | "SKIP" | "CLASSIFY_INTENT" | "CHECK_DOCUMENTS" | "APPLY_MANAGER_ACTION"
    reminder_count: Optional[int]
    last_reminder_at: Optional[str]
    last_reminder_type: Optional[str]
    last_reminder_body: Optional[str]
    notification_status: Optional[str]

    # Phase 3 & 5: Manager Review, Intervention & Human Escalation State (SDD Section 8 & 12)
    manager_notification_id: Optional[int]
    manager_notification_status: Optional[str]
    manager_id: Optional[str]
    escalation_required: Optional[bool]
    escalation_id: Optional[int]
    escalation_reason: Optional[str]
    escalation_priority: Optional[str]
    escalation_status: Optional[str]
    escalation_description: Optional[str]
    manager_action: Optional[str]  # "APPROVE_CONTINUATION" | "REJECT_CONTINUATION" | "REQUEST_MORE_INFORMATION" | "NEGOTIATE" | "CLOSE_CASE"
    manager_notes: Optional[str]
    clarification_question: Optional[str]
    final_response: Optional[str]

    # Phase 4: Renewal Document Tracking State (SDD Section 12)
    required_documents: Optional[List[str]]
    received_documents: Optional[List[Dict[str, Any]]]
    missing_documents: Optional[List[str]]
    document_status: Optional[str]  # "PENDING" | "PARTIALLY_SUBMITTED" | "UNDER_REVIEW" | "COMPLETE"
    document_request_message: Optional[str]
    document_exception: Optional[bool]

    # Operational and Conversational State
    workflow_error: Optional[str]
    messages: List[Dict[str, Any]]
    final_response: Optional[str]
    is_complete: bool
    logs: List[str]
