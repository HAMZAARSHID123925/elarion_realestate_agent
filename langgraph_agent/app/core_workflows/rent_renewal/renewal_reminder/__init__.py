"""
Renewal Reminder Module — Phase 2 of Workflow #4 (Lease/Renewal).

Handles template rendering, multi-channel dispatch (Email, WhatsApp, Mock),
idempotent reminder history tracking, and batch processing of Phase 1 expiry events.
"""
from app.core_workflows.rent_renewal.renewal_reminder.service import run_renewal_reminder_dispatch
from app.core_workflows.rent_renewal.renewal_reminder.templates import render_renewal_reminder_message

__all__ = ["run_renewal_reminder_dispatch", "render_renewal_reminder_message"]
