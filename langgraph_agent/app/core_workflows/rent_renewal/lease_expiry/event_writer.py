"""
Expiry Event Writer — Phase 1, Workflow #4.

Idempotent event persistence. Delegates to the repository for actual
DB operations. Handles conflict (duplicate) gracefully.
"""
import logging
from datetime import date
from typing import Dict, Any, Optional

from app.core_workflows.rent_renewal.lease_expiry.config import EXPIRED_WINDOW_VALUE
from app.core_workflows.rent_renewal.lease_expiry import repository

logger = logging.getLogger(__name__)


def _build_event_name(window_days: int) -> str:
    """Build a standardized event name from a window value."""
    if window_days == EXPIRED_WINDOW_VALUE:
        return "LEASE_EXPIRED"
    return f"LEASE_EXPIRY_{window_days}_DAYS"


async def write_expiry_event(
    lease_id: str,
    tenant_id: str,
    property_id: str,
    expiry_date: date,
    days_remaining: int,
    window_days: int,
    event_date: date,
    run_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Write a single expiry event idempotently.

    Returns True if a new event was created, False if duplicate (already existed).
    """
    event_name = _build_event_name(window_days)

    inserted = await repository.insert_expiry_event(
        event_name=event_name,
        lease_id=lease_id,
        tenant_id=tenant_id,
        property_id=property_id,
        expiry_date=expiry_date,
        days_remaining=days_remaining,
        window_days=window_days,
        event_date=event_date,
        run_id=run_id,
        metadata=metadata,
    )

    if inserted:
        logger.info(
            "Created expiry event: lease=%s window=%d event=%s days_remaining=%d",
            lease_id,
            window_days,
            event_name,
            days_remaining,
        )
    else:
        logger.info(
            "Duplicate skipped: lease=%s window=%d (already recorded)",
            lease_id,
            window_days,
        )

    return inserted
