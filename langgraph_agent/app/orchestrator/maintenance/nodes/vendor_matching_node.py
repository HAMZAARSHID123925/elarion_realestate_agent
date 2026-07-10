import json
import logging
from typing import Dict, Any

from app.orchestrator.maintenance.state import MaintenanceState
from app.orchestrator.maintenance.mcp_client import mcp_client

logger = logging.getLogger(__name__)


async def vendor_matching_node(state: MaintenanceState) -> Dict[str, Any]:
    """Calls MCP assign_vendor tool to run the routing engine and propose a candidate.

    Runs after ticket_creation, so it relies on created_ticket_id and db_property_id
    already being present in state (set by ticket_creation_node).
    """
    payload = state.get("ticket_payload", {})

    ticket_id = state.get("created_ticket_id")
    property_id = state.get("db_property_id")

    if not ticket_id:
        logger.error("[VENDOR MATCHING] Missing created_ticket_id in state, cannot match vendor.")
        return {"assignment_status": "NEEDS_MANUAL_ASSIGNMENT", "assignment_strategy_used": "ERROR"}

    args = {
        "ticket_id": ticket_id,
        "category": payload.get("category") or "general",
        "property_id": property_id or payload.get("unit_id"),  # fallback for safety, not expected in normal flow
        "urgency": payload.get("urgency") or "low",
    }

    print(f"\n[VENDOR MATCHING] -> Calling MCP assign_vendor with args: {args}")

    try:
        result_json = await mcp_client.call_tool("assign_vendor", args)
        if not result_json:
            return {"assignment_status": "NEEDS_MANUAL_ASSIGNMENT", "assignment_strategy_used": "ERROR"}

        result = json.loads(result_json)
        print(f"  [MCP RESPONSE] -> {result}")

        if result.get("status") == "matched":
            return {
                "vendor_candidate": result.get("vendor"),
                "assignment_strategy_used": result.get("strategy"),
                "assignment_status": "UNASSIGNED",  # still pending human approval
            }
        elif result.get("status") == "needs_manual_assignment":
            return {
                "assignment_status": "NEEDS_MANUAL_ASSIGNMENT",
                "assignment_strategy_used": "EXHAUSTED",
                "assignment_attempts_log": result.get("attempt_history", []),
            }
        else:
            error_msg = result.get("message", "Unknown assignment error")
            print(f"  [MCP ERROR from Server] -> {error_msg}")
            return {"assignment_status": "NEEDS_MANUAL_ASSIGNMENT", "assignment_strategy_used": "ERROR"}

    except Exception as e:
        logger.error(f"  [MCP EXCEPTION] -> {e}")
        return {"assignment_status": "NEEDS_MANUAL_ASSIGNMENT", "assignment_strategy_used": "ERROR"}
