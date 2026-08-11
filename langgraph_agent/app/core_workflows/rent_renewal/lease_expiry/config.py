"""
Expiry Window Configuration — Phase 1, Workflow #4.

Loads configurable expiry windows from environment variables so that
window values can be changed without a code deploy.

Defaults: 90, 60, 30, 7 days before lease expiry.

Environment variables:
    LEASE_EXPIRY_WINDOWS       — comma-separated integers (e.g. "90,60,30,7")
    LEASE_EXPIRY_SCAN_TIMEZONE — IANA timezone name (e.g. "Asia/Karachi", default "UTC")
"""
import os
import logging
from typing import List
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------
DEFAULT_EXPIRY_WINDOWS = [90, 60, 30, 7]
DEFAULT_TIMEZONE = "UTC"

# The special window value used when a lease is already past its expiry date
EXPIRED_WINDOW_VALUE = 0


def load_expiry_windows() -> List[int]:
    """
    Load and validate expiry window configuration.

    Returns a sorted (descending), deduplicated list of positive integers.
    """
    raw = os.getenv("LEASE_EXPIRY_WINDOWS", "")
    if not raw.strip():
        windows = list(DEFAULT_EXPIRY_WINDOWS)
    else:
        try:
            parsed = [int(v.strip()) for v in raw.split(",") if v.strip()]
            # Filter out non-positive values
            windows = [w for w in parsed if w > 0]
            if not windows:
                logger.warning(
                    "LEASE_EXPIRY_WINDOWS contained no valid positive integers, "
                    "falling back to defaults: %s",
                    DEFAULT_EXPIRY_WINDOWS,
                )
                windows = list(DEFAULT_EXPIRY_WINDOWS)
        except ValueError:
            logger.warning(
                "LEASE_EXPIRY_WINDOWS could not be parsed ('%s'), "
                "falling back to defaults: %s",
                raw,
                DEFAULT_EXPIRY_WINDOWS,
            )
            windows = list(DEFAULT_EXPIRY_WINDOWS)

    # Deduplicate and sort descending (largest window first)
    windows = sorted(set(windows), reverse=True)
    logger.debug("Loaded expiry windows: %s", windows)
    return windows


def load_scan_timezone() -> ZoneInfo:
    """
    Load the configured business timezone for expiry date calculations.

    Returns a ZoneInfo instance.
    """
    tz_name = os.getenv("LEASE_EXPIRY_SCAN_TIMEZONE", DEFAULT_TIMEZONE).strip()
    try:
        tz = ZoneInfo(tz_name)
    except (KeyError, Exception):
        logger.warning(
            "Invalid LEASE_EXPIRY_SCAN_TIMEZONE '%s', falling back to UTC",
            tz_name,
        )
        tz = ZoneInfo("UTC")
    logger.debug("Using scan timezone: %s", tz)
    return tz
