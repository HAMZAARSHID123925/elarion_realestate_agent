"""
Renewal Reminder Service — Phase 2, Workflow #4.

Batch orchestration service that consumes PENDING lease_expiry_events,
renders message templates, dispatches notifications via configured channels,
records persistent reminder history, and updates event statuses.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.core_workflows.rent_renewal.renewal_reminder.templates import render_renewal_reminder_message
from app.core_workflows.rent_renewal.renewal_reminder.channels import dispatch_reminder
from app.core_workflows.rent_renewal.renewal_reminder.config import get_default_channel
from app.core_workflows.rent_renewal.renewal_reminder import repository

logger = logging.getLogger(__name__)


def _infer_channel(contact: str, default_channel: str) -> str:
    """Infers communication channel based on recipient format."""
    if "@" in contact:
        return "email"
    elif any(ch.isdigit() for ch in contact):
        return "whatsapp"
    return default_channel


async def run_renewal_reminder_dispatch() -> Dict[str, Any]:
    """
    Executes a batch run to dispatch reminders for all PENDING expiry events.

    Returns:
        Summary dict containing counts of processed, sent, failed, and details.
    """
    default_channel = get_default_channel()
    logger.info("--- Starting Renewal Reminder Batch Dispatch ---")

    try:
        pending_events = await repository.get_pending_expiry_events()
    except Exception as e:
        logger.error("Failed to fetch pending expiry events: %s", e, exc_info=True)
        return {
            "status": "FAILED",
            "events_scanned": 0,
            "reminders_sent": 0,
            "errors_count": 1,
            "error": str(e),
        }

    summary: Dict[str, Any] = {
        "status": "COMPLETED",
        "events_scanned": len(pending_events),
        "reminders_sent": 0,
        "reminders_failed": 0,
        "errors_count": 0,
        "details": [],
    }

    logger.info("Found %d pending expiry events to process.", len(pending_events))

    for event in pending_events:
        event_id = event["event_id"]
        lease_id = event["lease_id"]
        tenant_id = event["tenant_id"]
        property_id = event["property_id"]
        window_days = event["window_days"]
        days_remaining = event["days_remaining"]
        expiry_date = event["expiry_date"]
        expiry_date_str = str(expiry_date)
        tenant_name = event["tenant_name"]
        tenant_contact = event["tenant_contact"] or "tenant@example.com"
        property_address = event["property_address"]
        monthly_rent = float(event.get("monthly_rent") or 0.0)
        reminder_type = event["event_name"]

        try:
            # 1. Render message
            msg = render_renewal_reminder_message(
                window_days=window_days,
                tenant_name=tenant_name,
                property_address=property_address,
                expiry_date_str=expiry_date_str,
                monthly_rent=monthly_rent,
                days_remaining=days_remaining,
            )

            # 2. Determine channel
            channel = _infer_channel(tenant_contact, default_channel)

            # 3. Dispatch
            dispatch_result = await dispatch_reminder(
                recipient=tenant_contact,
                subject=msg["subject"],
                body=msg["body"],
                channel=channel,
            )

            is_success = dispatch_result.get("success", False)
            dispatch_status = dispatch_result.get("status", "SENT")
            error_msg = dispatch_result.get("error")

            # 4. Record reminder history
            reminder_id = await repository.record_renewal_reminder(
                lease_id=lease_id,
                tenant_id=tenant_id,
                property_id=property_id,
                channel=channel,
                recipient=tenant_contact,
                reminder_type=reminder_type,
                message_body=msg["body"],
                status=dispatch_status,
                event_id=event_id,
                error_message=error_msg,
                metadata={
                    "subject": msg["subject"],
                    "window_days": window_days,
                    "days_remaining": days_remaining,
                    "message_id": dispatch_result.get("message_id"),
                },
            )

            # 5. Update event status
            new_event_status = "SENT" if is_success else "FAILED"
            await repository.mark_expiry_event_status(event_id, new_event_status)

            if is_success:
                summary["reminders_sent"] += 1
                logger.info(
                    "Reminder #%d sent to tenant %s (%s) for lease %s [type=%s, channel=%s]",
                    reminder_id, tenant_name, tenant_contact, lease_id, reminder_type, channel
                )
            else:
                summary["reminders_failed"] += 1
                logger.warning(
                    "Reminder dispatch failed for lease %s: %s", lease_id, error_msg
                )

            summary["details"].append({
                "event_id": event_id,
                "lease_id": lease_id,
                "tenant_id": tenant_id,
                "reminder_id": reminder_id,
                "status": dispatch_status,
                "channel": channel,
                "error": error_msg,
            })

        except Exception as e:
            logger.error(
                "Error processing reminder for event %s (lease %s): %s",
                event_id, lease_id, e, exc_info=True
            )
            summary["errors_count"] += 1
            summary["reminders_failed"] += 1
            summary["details"].append({
                "event_id": event_id,
                "lease_id": lease_id,
                "status": "ERROR",
                "error": str(e),
            })
            # Attempt to mark event as FAILED
            try:
                await repository.mark_expiry_event_status(event_id, "FAILED")
            except Exception:
                pass

    logger.info(
        "--- Renewal Reminder Batch Complete: scanned=%d sent=%d failed=%d errors=%d ---",
        summary["events_scanned"],
        summary["reminders_sent"],
        summary["reminders_failed"],
        summary["errors_count"],
    )

    return summary
