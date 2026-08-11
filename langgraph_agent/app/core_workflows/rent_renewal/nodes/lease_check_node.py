"""
Lease Check Node — Workflow #4.
Evaluates lease end date, calculates days remaining until expiry,
and classifies the expiry stage.
"""
import logging
from datetime import datetime, date
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState

logger = logging.getLogger(__name__)


def _parse_date(date_val: Any) -> date:
    if isinstance(date_val, date):
        return date_val
    if isinstance(date_val, str):
        if "T" in date_val:
            return datetime.fromisoformat(date_val).date()
        return datetime.strptime(date_val, "%Y-%m-%d").date()
    return date.today()


def lease_check_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: lease_check_node
    Evaluates lease end date and assigns days_to_expiry & expiry_stage.
    """
    logs = state.get("logs", [])
    tenant_id = state.get("tenant_id", "unknown")
    lease_end_date_raw = state.get("lease_end_date")

    today = date.today()
    if lease_end_date_raw:
        expiry_date = _parse_date(lease_end_date_raw)
        days_to_expiry = (expiry_date - today).days
    else:
        days_to_expiry = state.get("days_to_expiry", 90)

    # Determine expiry stage
    if days_to_expiry <= 0:
        expiry_stage = "EXPIRED"
    elif days_to_expiry <= 7:
        expiry_stage = "7_DAYS"
    elif days_to_expiry <= 30:
        expiry_stage = "30_DAYS"
    elif days_to_expiry <= 60:
        expiry_stage = "60_DAYS"
    elif days_to_expiry <= 90:
        expiry_stage = "90_DAYS"
    else:
        expiry_stage = "FUTURE"

    logs.append(f"[lease_check_node] Tenant {tenant_id}: days_to_expiry={days_to_expiry}, stage={expiry_stage}")

    return {
        "days_to_expiry": days_to_expiry,
        "expiry_stage": expiry_stage,
        "renewal_status": state.get("renewal_status") or "APPROACHING_EXPIRY",
        "is_complete": False,
        "logs": logs,
    }
