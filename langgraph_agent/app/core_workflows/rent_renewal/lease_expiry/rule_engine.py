"""
Expiry Rule Engine — Phase 1, Workflow #4.

Pure, deterministic classification logic. No database access, no LLM,
no side effects. Fully unit-testable in isolation.

Given a lease's expiry date, today's business date, and a list of
configured windows, determines which windows the lease has crossed.
"""
import logging
from datetime import date
from typing import List, Optional, Tuple

from app.core_workflows.rent_renewal.lease_expiry.config import EXPIRED_WINDOW_VALUE

logger = logging.getLogger(__name__)


class InvalidExpiryDateError(Exception):
    """Raised when a lease has a missing or invalid expiry date."""
    pass


def compute_days_remaining(expiry_date: date, today: date) -> int:
    """
    Compute days remaining until lease expiry.

    Uses calendar-date subtraction (not timedelta over datetimes)
    to avoid DST / time-of-day drift (Phase 1 §23).

    Returns:
        Integer number of calendar days. Negative means already expired.
    """
    return (expiry_date - today).days


def classify_lease(
    expiry_date: Optional[date],
    today: date,
    windows: List[int],
) -> Tuple[int, List[int]]:
    """
    Classify a lease against configured expiry windows.

    Args:
        expiry_date: The lease's end date. None/invalid raises InvalidExpiryDateError.
        today: The current business date.
        windows: Sorted (descending) list of positive integer window values
                 (e.g. [90, 60, 30, 7]).

    Returns:
        Tuple of (days_remaining, list_of_crossed_windows).
        crossed_windows contains only windows where days_remaining <= window_value.
        If the lease is already expired (days_remaining <= 0), the special
        EXPIRED_WINDOW_VALUE (0) is included.

    Raises:
        InvalidExpiryDateError: if expiry_date is None or not a date instance.
    """
    if expiry_date is None:
        raise InvalidExpiryDateError("Lease expiry date is None")

    if not isinstance(expiry_date, date):
        raise InvalidExpiryDateError(
            f"Lease expiry date is not a valid date: {expiry_date!r}"
        )

    days_remaining = compute_days_remaining(expiry_date, today)
    crossed_windows: List[int] = []

    for window in windows:
        if days_remaining <= window:
            crossed_windows.append(window)

    # Handle already-expired leases as a distinct condition (Phase 1 §18)
    if days_remaining <= 0 and EXPIRED_WINDOW_VALUE not in crossed_windows:
        crossed_windows.append(EXPIRED_WINDOW_VALUE)

    return days_remaining, crossed_windows
