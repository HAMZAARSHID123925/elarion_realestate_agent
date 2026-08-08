from typing import Dict, Any
from langgraph.types import interrupt

from app.core_workflows.maintenance.state import MaintenanceState


async def human_approval_node(state: MaintenanceState) -> Dict[str, Any]:
    """Pauses the graph and asks a human coordinator to approve the proposed vendor.

    Uses LangGraph's native interrupt() so execution suspends cleanly and resumes via
    the graph's checkpointer (MemorySaver), instead of blocking on a raw input() call
    inside the node. This is what makes the pause/resume survive process-level state
    correctly, and is the same mechanism you'd use later if this becomes a real
    dashboard button instead of a terminal prompt.
    """
    if state.get("assignment_status") == "NEEDS_MANUAL_ASSIGNMENT":
        # No candidate was found by the routing engine — nothing to approve,
        # this ticket already needs a human to hand-pick a vendor.
        return {"human_approval_status": "skipped"}

    vendor = state.get("vendor_candidate", {})
    payload = state.get("ticket_payload", {})

    approval_request = {
        "message": "Approve vendor assignment for this maintenance ticket?",
        "ticket_id": state.get("created_ticket_id"),
        "unit_id": payload.get("unit_id"),
        "category": payload.get("category"),
        "description": payload.get("description"),
        "urgency": payload.get("urgency"),
        "strategy_used": state.get("assignment_strategy_used"),
        "proposed_vendor": vendor,
    }

    # Execution pauses here. The caller resumes with Command(resume=<value>).
    decision = interrupt(approval_request)

    normalized = str(decision).strip().lower()
    if normalized in ("yes", "y", "approve", "approved", "true"):
        return {"human_approval_status": "approved"}
    else:
        return {"human_approval_status": "rejected"}
