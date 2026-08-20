"""
Alert & Notification Dispatcher — Phase 5 Scheduling & Alerting.

Handles multi-domain alerting for:
  1. Chronic Rent Arrears Manager Escalations (Day 35+ non-responsive)
  2. Unassigned Emergency Maintenance Tickets (SLA breaches)
  3. Background Job Dead-Letter & Failure Alerts
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AlertService:
    """Dispatches and tracks high-priority operational alerts across all platform domains."""

    def __init__(self):
        self._alert_history: List[Dict[str, Any]] = []

    def _record_alert(self, alert_type: str, severity: str, message: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        alert_record = {
            "alert_id": f"ALT-{len(self._alert_history) + 1:04d}",
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "metadata": metadata,
            "dispatched_at": datetime.utcnow().isoformat(),
            "status": "DISPATCHED"
        }
        self._alert_history.append(alert_record)
        # In production, dispatch via Email / SMS / Webhook / Slack
        logger.warning(
            f"[ALERT DISPATCHED] [{severity}] {alert_type}: {message} | Metadata: {metadata}"
        )
        return alert_record

    def send_rent_escalation_alert(
        self,
        tenant_id: str,
        tenant_name: str,
        property_address: str,
        rent_amount: float,
        days_overdue: int,
        reason: str
    ) -> Dict[str, Any]:
        """
        Dispatches escalation dossier when a tenant reaches chronic overdue status (Day 35+).
        """
        dossier = {
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "property_address": property_address,
            "rent_amount": rent_amount,
            "days_overdue": days_overdue,
            "escalation_reason": reason
        }
        msg = f"Tenant {tenant_name} ({tenant_id}) is {days_overdue} days overdue (PKR {rent_amount:,.2f}). Human manager intervention required."
        return self._record_alert(
            alert_type="RENT_ARREARS_ESCALATION",
            severity="HIGH",
            message=msg,
            metadata=dossier
        )

    def send_maintenance_emergency_alert(
        self,
        ticket_id: str,
        category: str,
        description: str,
        urgency: str,
        unassigned_hours: float
    ) -> Dict[str, Any]:
        """
        Dispatches immediate alert when an emergency maintenance ticket breaches SLA.
        """
        meta = {
            "ticket_id": ticket_id,
            "category": category,
            "description": description,
            "urgency": urgency,
            "unassigned_hours": unassigned_hours
        }
        msg = f"EMERGENCY Ticket {ticket_id} ({category}) has remained UNASSIGNED for {unassigned_hours:.1f} hours! Description: {description}"
        return self._record_alert(
            alert_type="MAINTENANCE_EMERGENCY_SLA_BREACH",
            severity="CRITICAL",
            message=msg,
            metadata=meta
        )

    def send_dead_letter_alert(
        self,
        job_name: str,
        error_message: str,
        attempts: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Dispatches system alert when a background job fails all retry attempts.
        """
        meta = {
            "job_name": job_name,
            "error": error_message,
            "attempts": attempts,
            "context": context or {}
        }
        msg = f"Background job '{job_name}' permanently failed after {attempts} retries. Error: {error_message}"
        return self._record_alert(
            alert_type="JOB_DEAD_LETTER_FAILURE",
            severity="ERROR",
            message=msg,
            metadata=meta
        )

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent alert history."""
        return list(reversed(self._alert_history[-limit:]))

    def clear_history(self) -> None:
        """Clears history (for testing)."""
        self._alert_history.clear()


# Shared singleton alert service
alert_service = AlertService()
