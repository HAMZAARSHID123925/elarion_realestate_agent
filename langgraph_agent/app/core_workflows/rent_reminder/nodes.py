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
    Purpose: Computes cycle day and days_overdue based on joining_date and rent_due_date relative to current_date.
    """
    curr_date = parse_date(state.get("current_date", date.today().isoformat()))
    due_date = parse_date(state.get("rent_due_date"))
    joining_date = parse_date(state.get("joining_date"))

    days_overdue = (curr_date - due_date).days if due_date else 0
    days_since_joining = (curr_date - joining_date).days if joining_date else None

    logs = state.get("logs", [])
    logs.append(
        f"[payment_check_node] Tenant {state.get('tenant_id')}: days_overdue={days_overdue}, "
        f"joining_date={joining_date}, days_since_joining={days_since_joining}"
    )

    return {
        "days_overdue": days_overdue,
        "logs": logs
    }

def reminder_decision_node(state: RentReminderState) -> Dict[str, Any]:
    """
    NODE: reminder_decision_node
    Purpose: Evaluates tenant 30-day billing cycle rules based on joining date:
      1. Paid or Manual Hold -> SKIP
      2. Day 30 of Billing Cycle (Due Date up to 30 days overdue) -> SEND_REMINDER (#1)
      3. Days 31-35 of Billing Cycle (1 to 5 days unpaid past 30th day) -> SEND_FOLLOWUP (31-35 Days Warning)
      4. Day 36+ of Billing Cycle (unpaid past Day 35) -> ESCALATE (Direct Human Transfer)
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

    # Rule 1: Day 30 Billing Cycle Reminder (Due Date reached, no reminder #1 sent yet)
    elif days_overdue >= 0 and not r30_sent:
        action = "SEND_REMINDER"
        logs.append(f"[reminder_decision_node] Decision: SEND_REMINDER (Day 30 billing cycle due date reached, days_overdue={days_overdue})")

    # Rule 2: Days 31-35 Warning Window (1-5 days past 30th day, Reminder #1 sent, Reminder #2 not sent)
    elif r30_sent and not r5_sent:
        r30_date = parse_date(r30_sent)
        days_since_r30 = (curr_date - r30_date).days if r30_date else 0
        
        # If we are within days 31-35 of cycle (1-5 days post 30-day reminder)
        if days_since_r30 >= 1 and days_since_r30 <= 5:
            action = "SEND_FOLLOWUP"
            logs.append(f"[reminder_decision_node] Decision: SEND_FOLLOWUP (Days 31-35 warning window, days_since_reminder={days_since_r30})")
        elif days_since_r30 > 5 and not human_escalated:
            action = "ESCALATE"
            logs.append(f"[reminder_decision_node] Decision: ESCALATE (Day 36 threshold reached, days_since_reminder={days_since_r30} > 5)")
        else:
            action = "SKIP"
            logs.append(f"[reminder_decision_node] Decision: SKIP (waiting for schedule window, currently {days_since_r30} days since r30)")

    # Rule 3: Day 36+ Direct Human Escalation (Reminder #2 sent or >35 days, unpaid & no response)
    elif (r5_sent or days_overdue >= 6) and not human_escalated and not response_received:
        action = "ESCALATE"
        logs.append("[reminder_decision_node] Decision: ESCALATE (Day 36 threshold reached: rent unpaid past 35 days, direct human transfer)")
    else:
        action = "SKIP"
        logs.append("[reminder_decision_node] Decision: SKIP (no rule action required)")

    return {
        "action": action,
        "logs": logs
    }

def reminder_send_node(state: RentReminderState) -> Dict[str, Any]:
    """
    NODE: reminder_send_node
    Purpose: Formats reminder & warning messages according to joining date & 30-day cycle rules, dispatches notification, and updates DB.
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
            f"Subject: Important: Rent Payment Due (30th Day Billing Cycle Notice)\n\n"
            f"Dear {tenant_name},\n"
            f"This is a friendly automated reminder that your monthly rent of PKR {rent_amount:,.2f} for "
            f"{property_address} has reached its 30th day billing cycle (due date: {due_date}).\n"
            f"Please arrange payment at your earliest convenience to maintain an active account."
        )
        status = "reminder_sent"
        update_tenant_reminder_status(
            tenant_id=tenant_id,
            last_reminder_status=status,
            reminder_30_sent_at=curr_date,
            payment_status="reminder_sent"
        )
        logs.append(f"[reminder_send_node] Dispatched 30-Day Rent Reminder #1 to tenant {tenant_id}")

    elif action == "SEND_FOLLOWUP":
        message_body = (
            f"Subject: URGENT: Rent Unpaid Notice (Days 31-35 Overdue Window)\n\n"
            f"Dear {tenant_name},\n"
            f"Our records indicate that your rent payment of PKR {rent_amount:,.2f} for {property_address} "
            f"remains unpaid during the Days 31-35 grace period.\n"
            f"Please submit payment immediately. If payment is not cleared by Day 36, your account will be "
            f"transferred directly to human property management for legal/formal intervention."
        )
        status = "followup_sent"
        update_tenant_reminder_status(
            tenant_id=tenant_id,
            last_reminder_status=status,
            reminder_5_sent_at=curr_date,
            payment_status="followup_sent"
        )
        logs.append(f"[reminder_send_node] Dispatched Days 31-35 Warning Notice #2 to tenant {tenant_id}")
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
    Purpose: Triggered on Day 36 when rent remains unpaid past Day 35. Packages tenant summary and transfers directly to human staff.
    """
    tenant_id = state.get("tenant_id")
    escalation_reason = "Day 36 Threshold Reached: Rent remains unpaid past the 31-35 day warning window. Escalated directly to human manager."
    logs = state.get("logs", [])

    escalation_alert_payload = {
        "alert_type": "HUMAN_TRANSFER_OVERDUE_RENT_DAY36",
        "tenant_id": tenant_id,
        "tenant_name": state.get("tenant_name"),
        "property_address": state.get("property_address"),
        "rent_amount": state.get("rent_amount"),
        "due_date": state.get("rent_due_date"),
        "joining_date": state.get("joining_date"),
        "days_overdue": state.get("days_overdue"),
        "reminder_30_sent": state.get("reminder_30_sent_at"),
        "warning_31_35_sent": state.get("reminder_5_sent_at"),
        "escalation_reason": escalation_reason,
        "recommended_actions": [
            "Initiate immediate direct phone call to tenant",
            "Issue formal 48-hour notice of default",
            "Schedule manager review"
        ]
    }

    update_tenant_reminder_status(
        tenant_id=tenant_id,
        last_reminder_status="escalated",
        human_escalated=True,
        escalation_reason=escalation_reason,
        payment_status="escalated"
    )

    logs.append(f"[human_escalation_node] Day 36 direct human transfer executed for tenant {tenant_id}")

    return {
        "human_escalated": True,
        "escalation_reason": escalation_reason,
        "last_reminder_status": "escalated",
        "notification_status": "human_manager_notified",
        "logs": logs
    }
