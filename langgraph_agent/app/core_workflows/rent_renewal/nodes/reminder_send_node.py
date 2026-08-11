"""
Reminder Send Node — Workflow #4.
Renders tailored renewal reminder message and dispatches it via channel.
"""
import logging
from datetime import datetime, date
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState
from app.core_workflows.rent_renewal.renewal_reminder.templates import render_renewal_reminder_message
from app.core_workflows.rent_renewal.renewal_reminder.channels import dispatch_reminder

logger = logging.getLogger(__name__)


async def renewal_reminder_send_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: renewal_reminder_send_node
    Renders template, dispatches reminder, and updates notification timestamps.
    """
    logs = state.get("logs", [])
    tenant_name = state.get("tenant_name", "Resident")
    tenant_contact = state.get("tenant_contact") or state.get("tenant_id") or "tenant@example.com"
    property_address = state.get("property_address", "Your Residence")
    expiry_date_str = str(state.get("lease_end_date", date.today().isoformat()))
    monthly_rent = float(state.get("monthly_rent") or 0.0)
    days_remaining = state.get("days_to_expiry", 90)
    expiry_stage = state.get("expiry_stage", "90_DAYS")

    stage_to_window = {
        "EXPIRED": 0,
        "7_DAYS": 7,
        "30_DAYS": 30,
        "60_DAYS": 60,
        "90_DAYS": 90,
    }
    window_days = stage_to_window.get(expiry_stage, 90)

    msg = render_renewal_reminder_message(
        window_days=window_days,
        tenant_name=tenant_name,
        property_address=property_address,
        expiry_date_str=expiry_date_str,
        monthly_rent=monthly_rent,
        days_remaining=days_remaining,
    )

    channel = "email" if "@" in tenant_contact else "whatsapp"
    dispatch_res = await dispatch_reminder(
        recipient=tenant_contact,
        subject=msg["subject"],
        body=msg["body"],
        channel=channel,
    )

    reminder_type = f"LEASE_EXPIRY_{expiry_stage}" if expiry_stage != "EXPIRED" else "LEASE_EXPIRED"
    curr_count = state.get("reminder_count", 0) + 1
    now_iso = datetime.now().isoformat()

    logs.append(
        f"[renewal_reminder_send_node] Dispatched {reminder_type} to {tenant_contact} "
        f"via {channel} (status={dispatch_res.get('status')})"
    )

    return {
        "renewal_status": "REMINDER_SENT",
        "reminder_count": curr_count,
        "last_reminder_at": now_iso,
        "last_reminder_type": reminder_type,
        "last_reminder_body": msg["body"],
        "notification_status": dispatch_res.get("status", "SENT"),
        "logs": logs,
    }
