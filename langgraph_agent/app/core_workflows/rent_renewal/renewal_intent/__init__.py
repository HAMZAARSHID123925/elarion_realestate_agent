"""
Renewal Intent Module — Phase 3 of Workflow #4 (Lease/Renewal).

Interprets tenant responses, classifies renewal intent (YES, NO, UNCLEAR, NEGOTIATION),
manages manager notifications for Human-in-the-Loop reviews, and persists audit state.
"""
from app.core_workflows.rent_renewal.renewal_intent.classifier import (
    classify_renewal_intent,
    RenewalIntentResult,
)
from app.core_workflows.rent_renewal.renewal_intent.notifications import (
    notify_manager_of_renewal_intent,
)

__all__ = [
    "classify_renewal_intent",
    "RenewalIntentResult",
    "notify_manager_of_renewal_intent",
]
