"""
Human Escalation Module — Phase 5 of Workflow #4 (Lease/Renewal).

Establishes the Human-in-the-Loop boundary: detects escalation triggers,
creates durable escalation records, alerts property managers, and processes human decisions.
"""
from app.core_workflows.rent_renewal.human_escalation.config import (
    ESCALATION_REASONS,
    VALID_MANAGER_ACTIONS,
)
from app.core_workflows.rent_renewal.human_escalation.detector import (
    detect_escalation_requirement,
)
from app.core_workflows.rent_renewal.human_escalation.service import (
    trigger_human_escalation,
    process_manager_decision,
)

__all__ = [
    "ESCALATION_REASONS",
    "VALID_MANAGER_ACTIONS",
    "detect_escalation_requirement",
    "trigger_human_escalation",
    "process_manager_decision",
]
