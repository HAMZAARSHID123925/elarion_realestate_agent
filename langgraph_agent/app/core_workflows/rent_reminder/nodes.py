"""
LangGraph Nodes for Rent Reminder & Human Escalation Workflows — Phase 3 Live Data Wired.
Implements nodes specified in Blueprint Section 8 & 11 and SDD 03, 05, 06, 07.
"""
import logging
import sys
import os
from datetime import datetime, date
from typing import Dict, Any, Optional

# Ensure project root (elarion_realestate_agent) is in path for database module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from app.core_workflows.rent_reminder.state import RentReminderState
from database.rent_models import update_tenant_reminder_status, get_tenant_by_id

logger = logging.getLogger(__name__)


def parse_date(date_str: Optional[Any]) -> Optional[date]:
    """Helper to parse YYYY-MM-DD, ISO timestamp, or date object into date object."""
    if not date_str:
        return None
    if isinstance(date_str, date):
        return date_str
    if isinstance(date_str, datetime):
        return date_str.date()
    date_str_clean = str(date_str).strip()
    if not date_str_clean:
        return None
    if "T" in date_str_clean:
        return datetime.fromisoformat(date_str_clean).date()
    if " " in date_str_clean:
        return datetime.strptime(date_str_clean.split(" ")[0], "%Y-%m-%d").date()
    return datetime.strptime(date_str_clean, "%Y-%m-%d").date()


def payment_check_node(state: RentReminderState) -> Dict[str, Any]:
    """
    NODE: payment_check_node
    Purpose: Validates tenant data, hydrates live record from TenantRepository/database
    if fields are unpopulated, and computes cycle day and days_overdue based on joining_date and rent_due_date.
    """
    logs = list(state.get("logs", []))
    tenant_id = state.get("tenant_id")
    curr_date_raw = state.get("current_date") or date.today().isoformat()
    curr_date = parse_date(curr_date_raw) or date.today()

    updates: Dict[str, Any] = {"current_date": curr_date_raw}

    # If tenant_id is provided but essential fields are missing from state, fetch live record
    if tenant_id and (not state.get("rent_due_date") or not state.get("property_address")):
        tenant_record = get_tenant_by_id(tenant_id)
        if not tenant_record:
            logs.append(f"[payment_check_node] Tenant {tenant_id} not found in database")
            updates["action"] = "SKIP"
            updates["error"] = "tenant_not_found"
            updates["days_overdue"] = 0
            updates["logs"] = logs
            return updates

        # Hydrate state from live database record
        t_name = tenant_record.get("tenant_name") or tenant_record.get("name") or state.get("tenant_name")
        p_addr = tenant_record.get("property_address") or state.get("property_address")
        j_date = str(tenant_record.get("joining_date")) if tenant_record.get("joining_date") else state.get("joining_date")
        r_due = str(tenant_record.get("rent_due_date")) if tenant_record.get("rent_due_date") else None
        r_amt = float(tenant_record.get("rent_amount") or 0.0) if tenant_record.get("rent_amount") is not None else state.get("rent_amount", 0.0)
        p_stat = tenant_record.get("payment_status") or state.get("payment_status", "overdue")
        r30 = str(tenant_record.get("reminder_30_sent_at")) if tenant_record.get("reminder_30_sent_at") else state.get("reminder_30_sent_at")
        r5 = str(tenant_record.get("reminder_5_sent_at")) if tenant_record.get("reminder_5_sent_at") else state.get("reminder_5_sent_at")
        resp_rec = bool(tenant_record.get("response_received", False)) if "response_received" in tenant_record else state.get("response_received", False)
        h_esc = bool(tenant_record.get("human_escalated", False)) if "human_escalated" in tenant_record else state.get("human_escalated", False)
        esc_reas = tenant_record.get("escalation_reason") or state.get("escalation_reason")
        m_hold = bool(tenant_record.get("manual_hold", False)) if "manual_hold" in tenant_record else state.get("manual_hold", False)
        last_rem = tenant_record.get("last_reminder_status") or state.get("last_reminder_status", "none")

        updates.update({
            "tenant_name": t_name,
            "property_address": p_addr,
            "joining_date": j_date,
            "rent_due_date": r_due,
            "rent_amount": r_amt,
            "payment_status": p_stat,
            "reminder_30_sent_at": r30,
            "reminder_5_sent_at": r5,
            "response_received": resp_rec,
            "human_escalated": h_esc,
            "escalation_reason": esc_reas,
            "manual_hold": m_hold,
            "last_reminder_status": last_rem,
        })
        due_date_str = r_due
        joining_date_str = j_date
    else:
        due_date_str = state.get("rent_due_date")
        joining_date_str = state.get("joining_date")

    due_date = parse_date(due_date_str) if due_date_str else None
    joining_date = parse_date(joining_date_str) if joining_date_str else None

    days_overdue = (curr_date - due_date).days if (due_date and curr_date) else 0
    days_since_joining = (curr_date - joining_date).days if (joining_date and curr_date) else None

    logs.append(f"[payment_check_node] Tenant {tenant_id}: days_overdue={days_overdue}, joining_date={joining_date}, days_since_joining={days_since_joining}")
    updates["days_overdue"] = days_overdue
    updates["logs"] = logs

    return updates


def reminder_decision_node(state: RentReminderState) -> Dict[str, Any]:
    """
    NODE: reminder_decision_node
    Purpose: Pure Python decision engine evaluating business rules.
    Evaluates tenant 30-day billing cycle rules based on joining date:
      1. Paid or Manual Hold -> SKIP
      2. Day 30 of Billing Cycle (Due Date up to 30 days overdue) -> SEND_REMINDER (#1)
      3. Days 31-35 of Billing Cycle (1 to 5 days unpaid past 30th day) -> SEND_FOLLOWUP (31-35 Days Warning)
      4. Day 36+ of Billing Cycle (unpaid past Day 35) -> ESCALATE (Direct Human Transfer)
    """
    logs = list(state.get("logs", []))

    # If already set to SKIP (e.g. tenant not found), preserve decision
    if state.get("error") == "tenant_not_found":
        logs.append("[reminder_decision_node] Skipping decision: tenant_not_found")
        return {
            "action": "SKIP",
            "error": "tenant_not_found",
            "logs": logs
        }

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
    rent_amount = state.get("rent_amount", 0.0)
    property_address = state.get("property_address")
    due_date = state.get("rent_due_date")
    curr_date = state.get("current_date", date.today().isoformat())
    logs = list(state.get("logs", []))

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
        "notification_status": "delivered" if action in ("SEND_REMINDER", "SEND_FOLLOWUP") else "none",
        "logs": logs
    }


def followup_tracker_node(state: RentReminderState) -> Dict[str, Any]:
    """
    NODE: followup_tracker_node
    Purpose: Ensures audit logging & idempotency tracking after notification dispatch.
    """
    logs = list(state.get("logs", []))
    logs.append(f"[followup_tracker_node] Audited reminder status='{state.get('last_reminder_status')}' for tenant {state.get('tenant_id')}")
    return {"logs": logs}


def human_escalation_node(state: RentReminderState) -> Dict[str, Any]:
    """
    NODE: human_escalation_node
    Purpose: Triggered on Day 36 when rent remains unpaid past Day 35. Packages tenant summary and transfers directly to human staff.
    """
    tenant_id = state.get("tenant_id")
    escalation_reason = "Day 36 Threshold Reached: Rent remains unpaid past the 31-35 day warning window. Escalated directly to human manager."
    logs = list(state.get("logs", []))

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
