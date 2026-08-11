"""
Renewal Reminder Configuration — Phase 2, Workflow #4.

Loads channel defaults, from-address, and reminder rules from environment variables.
"""
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Default channel configuration
DEFAULT_RENEWAL_CHANNEL = "email"
DEFAULT_FROM_EMAIL = "renewals@elarion.com"
DEFAULT_MAX_REMINDERS_PER_CYCLE = 5


def get_default_channel() -> str:
    """Returns configured default communication channel (email, whatsapp, mock)."""
    return os.getenv("RENEWAL_DEFAULT_CHANNEL", DEFAULT_RENEWAL_CHANNEL).strip().lower()


def get_from_email_address() -> str:
    """Returns the sender email address for renewal reminders."""
    return os.getenv("FROM_EMAIL_ADDRESS", DEFAULT_FROM_EMAIL).strip()


def get_max_reminders_limit() -> int:
    """Returns max allowed reminders per lease renewal cycle."""
    try:
        return int(os.getenv("RENEWAL_MAX_REMINDERS", str(DEFAULT_MAX_REMINDERS_PER_CYCLE)))
    except ValueError:
        return DEFAULT_MAX_REMINDERS_PER_CYCLE
