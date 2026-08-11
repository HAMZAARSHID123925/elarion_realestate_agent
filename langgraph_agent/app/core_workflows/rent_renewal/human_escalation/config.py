"""
Human Escalation Configuration — Phase 5, Workflow #4.

Defines escalation reasons, priority levels, supported manager actions,
and default manager assignment settings.
"""
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Controlled escalation categories (SDD Section 6)
ESCALATION_REASONS = {
    "RENEWAL_APPROVAL_REQUIRED": {
        "label": "Renewal Authorization Required",
        "default_priority": "MEDIUM",
        "description": "Tenant confirmed renewal intent; property manager approval needed to finalize.",
    },
    "NEGOTIATION_REQUIRED": {
        "label": "Terms & Rent Negotiation",
        "default_priority": "HIGH",
        "description": "Tenant requested custom rent reduction, duration, or special conditions.",
    },
    "TENANT_REQUESTED_HUMAN": {
        "label": "Tenant Requested Manager Contact",
        "default_priority": "MEDIUM",
        "description": "Tenant explicitly requested to speak directly with a human property manager.",
    },
    "EXCEPTION_REQUEST": {
        "label": "Policy or Term Exception",
        "default_priority": "MEDIUM",
        "description": "Tenant requested an exception to standard renewal policies or payment terms.",
    },
    "DOCUMENT_ISSUE": {
        "label": "Document Verification Exception",
        "default_priority": "MEDIUM",
        "description": "Submitted documents are invalid, rejected, or missing after deadline.",
    },
    "WORKFLOW_ERROR": {
        "label": "Operational Exception",
        "default_priority": "HIGH",
        "description": "System anomaly or missing critical data required for automated processing.",
    },
    "OTHER": {
        "label": "General Escalation",
        "default_priority": "LOW",
        "description": "Other matters requiring property manager review.",
    },
}

# Supported manager decision actions (SDD Section 13)
VALID_MANAGER_ACTIONS = [
    "APPROVE_CONTINUATION",
    "REJECT_CONTINUATION",
    "REQUEST_MORE_INFORMATION",
    "NEGOTIATE",
    "CLOSE_CASE",
]

DEFAULT_MANAGER_ASSIGNMENT = "Property Manager"


def get_default_assigned_manager() -> str:
    """Returns the default manager assignment from environment or default."""
    return os.getenv("DEFAULT_PROPERTY_MANAGER", DEFAULT_MANAGER_ASSIGNMENT).strip()
