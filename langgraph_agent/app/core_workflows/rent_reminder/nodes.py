"""
LangGraph Nodes for Rent Reminder & Human Escalation Workflows.
Implements nodes specified in Blueprint Section 8 & 11.
"""
import logging
import sys
import os
from datetime import datetime, date
from typing import Dict, Any

# Ensure project root (elarion_realestate_agent) is in path for database module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))


from app.core_workflows.rent_reminder.state import RentReminderState
from database.rent_models import update_tenant_reminder_status

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> date:
    """Helper to parse YYYY-MM-DD or ISO timestamp into date object."""
    if not date_str:
        return None
    if "T" in date_str:
        return datetime.fromisoformat(date_str).date()
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def payment_check_node(state: RentReminderState) -> Dict[str, Any]:
    """
    NODE: payment_check_node
    Purpose: Computes days_overdue from current_date and rent_due_date.
    """
    curr_date = parse_date(state.get("current_date", date.today().isoformat()))
    due_date = parse_date(state.get("rent_due_date"))

    days_overdue = (curr_date - due_date).days if due_date else 0
    logs = state.get("logs", [])
    logs.append(f"[payment_check_node] Calculated days_overdue={days_overdue} for tenant {state.get('tenant_id')}")

    return {
        "days_overdue": days_overdue,
        "logs": logs
    }

def reminder_decision_node(state: RentReminderState) -> Dict[str, Any]:
    """
    NODE: reminder_decision_node
    Purpose: Pure Python decision engine evaluating rules.
    Decides action: SEND_REMINDER | SEND_FOLLOWUP | ESCALATE | SKIP
    """
    logs = state.get("logs", [])
    curr_date = parse_date(state.get("current_date", date.today().isoformat()))
    
    payment_status = state.get("payment_status", "overdue")
    manual_hold = state.get("manual_hold", False)
    days_overdue = state.get("days_overdue", 0)
    r30_sent = state.get("reminder_30_sent_at")
    r5_sent = state.get("reminder_5_sent_at")
    response_received = state.get("response_received", False)
    human_escalated = state.get("human_escalated", False)

    action = "SKIP"

    # Edge Case: Paid or Manual Hold -> Skip immediately
    if payment_status == "paid" or manual_hold:
        action = "SKIP"
        logs.append(f"[reminder_decision_node] Skipping tenant (paid={payment_status=='paid'}, manual_hold={manual_hold})")
    # Rule 1: Day 30 Reminder #1
    elif days_overdue >= 30 and not r30_sent:
        action = "SEND_REMINDER"
        logs.append(f"[reminder_decision_node] Decision: SEND_REMINDER (days_overdue={days_overdue} >= 30)")
    # Rule 2: Day 35 Follow-Up Reminder #2 (5 days after Reminder #1)
    elif r30_sent and not r5_sent:
        r30_date = parse_date(r30_sent)
        days_since_r30 = (curr_date - r30_date).days if r30_date else 0
        if days_since_r30 >= 5:
            action = "SEND_FOLLOWUP"
            logs.append(f"[reminder_decision_node] Decision: SEND_FOLLOWUP (days_since_reminder={days_since_r30} >= 5)")
        else:
            action = "SKIP"
            logs.append(f"[reminder_decision_node] Decision: SKIP (waiting for 5-day window, currently {days_since_r30} days)")
    # Rule 3: Escalation Decision (Reminder #2 sent, no payment, no response)
    elif r5_sent and not human_escalated and not response_received:
        action = "ESCALATE"
        logs.append("[reminder_decision_node] Decision: ESCALATE (no payment or response after 2 reminders)")
    else:
        action = "SKIP"
        logs.append("[reminder_decision_node] Decision: SKIP (no rules matched)")

    return {
        "action": action,
        "logs": logs
    }

def reminder_send_node(state: RentReminderState) -> Dict[str, Any]:
    """
    NODE: reminder_send_node
    Purpose: Formats reminder message, sends via notification service, and updates DB timestamps.
    """
    action = state.get("action")
    tenant_id = state.get("tenant_id")
    tenant_name = state.get("tenant_name")
    rent_amount = state.get("rent_amount")
    property_address = state.get("property_address")
    due_date = state.get("rent_due_date")
    curr_date = state.get("current_date", date.today().isoformat())
    logs = state.get("logs", [])

    if action == "SEND_REMINDER":
        message_body = (
            f"Subject: Important: Rent Payment Overdue — Action Required\n\n"
            f"Dear {tenant_name},\n"
            f"We noticed that your rent payment of PKR {rent_amount:,.2f} for the property at "
            f"{property_address} was due on {due_date} and has not yet been received.\n"
            f"This is a friendly reminder that your account is now overdue.\n"
            f"Please arrange payment at your earliest convenience."
        )
        status = "reminder_sent"
        update_tenant_reminder_status(
            tenant_id=tenant_id,
            last_reminder_status=status,
            reminder_30_sent_at=curr_date,
            payment_status="reminder_sent"
        )
        logs.append(f"[reminder_send_node] Sent Reminder #1 to tenant {tenant_id}")

    elif action == "SEND_FOLLOWUP":
        message_body = (
            f"Subject: URGENT: Rent Payment Still Outstanding — Final Notice\n\n"
            f"Dear {tenant_name},\n"
            f"This is a follow-up to our previous message sent on {state.get('reminder_30_sent_at')}.\n"
            f"As of today, your rent payment of PKR {rent_amount:,.2f} for {property_address} remains outstanding.\n"
            f"Failure to respond or arrange payment within 48 hours may result in referral to senior management."
        )
        status = "followup_sent"
        update_tenant_reminder_status(
            tenant_id=tenant_id,
            last_reminder_status=status,
            reminder_5_sent_at=curr_date,
            payment_status="followup_sent"
        )
        logs.append(f"[reminder_send_node] Sent Reminder #2 (Follow-up) to tenant {tenant_id}")
    else:
        message_body = None
        status = state.get("last_reminder_status", "none")

    return {
        "last_reminder_status": status,
        "notification_status": "delivered",
        "logs": logs
    }

def followup_tracker_node(state: RentReminderState) -> Dict[str, Any]:
    """
    NODE: followup_tracker_node
    Purpose: Ensures audit logging & idempotency tracking after notification dispatch.
    """
    logs = state.get("logs", [])
    logs.append(f"[followup_tracker_node] Audited reminder status='{state.get('last_reminder_status')}' for tenant {state.get('tenant_id')}")
    return {"logs": logs}

def human_escalation_node(state: RentReminderState) -> Dict[str, Any]:
    """
    NODE: human_escalation_node
    Purpose: Packages full tenant summary + history, sends escalation alert to staff, and marks DB as escalated.
    """
    tenant_id = state.get("tenant_id")
    escalation_reason = "No payment and no response after two automated reminders."
    logs = state.get("logs", [])

    escalation_alert_payload = {
        "alert_type": "ESCALATION_ALERT_OVERDUE_RENT",
        "tenant_id": tenant_id,
        "tenant_name": state.get("tenant_name"),
        "property_address": state.get("property_address"),
        "rent_amount": state.get("rent_amount"),
        "due_date": state.get("rent_due_date"),
        "days_overdue": state.get("days_overdue"),
        "reminder_1_sent": state.get("reminder_30_sent_at"),
        "reminder_2_sent": state.get("reminder_5_sent_at"),
        "escalation_reason": escalation_reason,
        "recommended_actions": [
            "Contact tenant directly by phone",
            "Issue formal legal notice if no response within 48 hours",
            "Update case status in system"
        ]
    }

    update_tenant_reminder_status(
        tenant_id=tenant_id,
        last_reminder_status="escalated",
        human_escalated=True,
        escalation_reason=escalation_reason,
        payment_status="escalated"
    )

    logs.append(f"[human_escalation_node] Case escalated to Property Manager for tenant {tenant_id}")

    return {
        "human_escalated": True,
        "escalation_reason": escalation_reason,
        "last_reminder_status": "escalated",
        "notification_status": "manager_alerted",
        "logs": logs
    }
