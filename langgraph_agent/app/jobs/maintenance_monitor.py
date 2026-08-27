"""
Maintenance SLA & Stale Ticket Monitor — Phase 5 Scheduling & Deduplication.

Periodic background job checking for unassigned emergency and standard maintenance tickets.
Features durable alert deduplication so the same ticket is alerted once per SLA window.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from database.maintenance_repository import maintenance_repository
from app.jobs.alerts import alert_service

logger = logging.getLogger(__name__)


async def check_stale_maintenance_tickets() -> Dict[str, Any]:
    """
    Scans open maintenance tickets to detect SLA breaches and unassigned tickets.
    - Emergency tickets unassigned > 1 hour -> CRITICAL alert (deduplicated).
    - Standard tickets unassigned > 24 hours -> WARNING alert (deduplicated).
    """
    logger.info("--- Starting Maintenance SLA & Stale Ticket Check ---")

    try:
        open_tickets = await maintenance_repository.list_tickets(status="OPEN", limit=100)
    except Exception as e:
        logger.error(f"Failed to query maintenance tickets for SLA check: {e}")
        return {
            "status": "FAILED",
            "error": str(e),
            "scanned": 0,
            "emergency_alerts": 0,
            "stale_alerts": 0
        }

    now = datetime.now(timezone.utc)
    emergency_alerts = 0
    stale_alerts = 0
    healthy = 0
    deduplicated_skips = 0

    for ticket in open_tickets:
        ticket_id = ticket.get("ticket_id")
        created_at = ticket.get("created_at")
        urgency = (ticket.get("urgency") or "low").lower()
        assignment_status = ticket.get("assignment_status", "UNASSIGNED")
        escalation_level = ticket.get("escalation_level")

        # Parse creation timestamp
        if isinstance(created_at, str):
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except Exception:
                created_dt = now
        elif isinstance(created_at, datetime):
            created_dt = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        else:
            created_dt = now

        age_hours = (now - created_dt).total_seconds() / 3600.0

        if assignment_status == "UNASSIGNED":
            if urgency == "high" and age_hours >= 1.0:
                if escalation_level == "EMERGENCY_SLA":
                    logger.debug(f"[MAINTENANCE SLA] Ticket {ticket_id} already escalated for EMERGENCY_SLA. Skipping duplicate alert.")
                    deduplicated_skips += 1
                else:
                    alert_service.send_maintenance_emergency_alert(
                        ticket_id=ticket_id,
                        category=ticket.get("category", "general"),
                        description=ticket.get("description", ""),
                        urgency=urgency,
                        unassigned_hours=age_hours
                    )
                    await maintenance_repository.record_ticket_escalation(ticket_id, "EMERGENCY_SLA")
                    emergency_alerts += 1

            elif age_hours >= 24.0:
                if escalation_level in ("STANDARD_SLA", "EMERGENCY_SLA"):
                    logger.debug(f"[MAINTENANCE SLA] Ticket {ticket_id} already escalated ({escalation_level}). Skipping duplicate alert.")
                    deduplicated_skips += 1
                else:
                    alert_service.send_maintenance_emergency_alert(
                        ticket_id=ticket_id,
                        category=ticket.get("category", "general"),
                        description=ticket.get("description", ""),
                        urgency=urgency,
                        unassigned_hours=age_hours
                    )
                    await maintenance_repository.record_ticket_escalation(ticket_id, "STANDARD_SLA")
                    stale_alerts += 1
            else:
                healthy += 1
        else:
            healthy += 1

    summary = {
        "status": "completed",
        "scanned": len(open_tickets),
        "emergency_alerts": emergency_alerts,
        "stale_alerts": stale_alerts,
        "deduplicated_skips": deduplicated_skips,
        "healthy": healthy
    }
    logger.info(
        f"--- Maintenance SLA Check Complete: scanned={summary['scanned']} "
        f"emergency={emergency_alerts} stale={stale_alerts} skips={deduplicated_skips} healthy={healthy} ---"
    )
    return summary
