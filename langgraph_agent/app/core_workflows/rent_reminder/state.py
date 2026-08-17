"""
State Schema for Rent Reminder & Human Escalation Subgraph.
"""
from typing import TypedDict, Optional, List

class RentReminderState(TypedDict, total=False):
    """
    TypedDict representing the state passed through the Rent Reminder
    & Human Escalation workflow nodes.
    """
    tenant_id: str
    tenant_name: str
    tenant_phone: str
    property_address: str
    rent_amount: float
    rent_due_date: str
    days_overdue: int
    reminder_30_sent_at: Optional[str]
    reminder_5_sent_at: Optional[str]
    response_received: bool
    human_escalated: bool
    escalation_reason: Optional[str]
    manual_hold: bool
    payment_status: str
    current_date: str
    action: str  # "SEND_REMINDER" | "SEND_FOLLOWUP" | "ESCALATE" | "SKIP"
    error: Optional[str]  # e.g. "tenant_not_found"
    last_reminder_status: str
    notification_status: str
    logs: List[str]
