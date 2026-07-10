import json
import logging
from typing import Dict, Any

from app.orchestrator.maintenance.state import MaintenanceState
from app.orchestrator.maintenance.mcp_client import mcp_client

logger = logging.getLogger(__name__)


async def vendor_assignment_node(state: MaintenanceState) -> Dict[str, Any]:
    """Commits the vendor assignment after human approval, or marks it rejected/manual."""
    approval = state.get("human_approval_status")
    ticket_id = state.get("created_ticket_id")
    vendor = state.get("vendor_candidate") or {}

    if approval == "skipped":
        # Already NEEDS_MANUAL_ASSIGNMENT from vendor_matching_node, nothing to commit.
        return {}

    if approval != "approved":
        print(f"\n[VENDOR ASSIGNMENT] -> Rejected by human coordinator for ticket {ticket_id}.")
        return {"assignment_status": "NEEDS_MANUAL_ASSIGNMENT"}

    vendor_id = vendor.get("vendor_id")
    if not vendor_id:
        logger.error("[VENDOR ASSIGNMENT] Approved but no vendor_id present in state.")
        return {"assignment_status": "NEEDS_MANUAL_ASSIGNMENT"}

    args = {
        "ticket_id": ticket_id,
        "vendor_id": vendor_id,
        "approved_by": "human_coordinator",
    }

    print(f"\n[VENDOR ASSIGNMENT] -> Calling MCP commit_assignment with args: {args}")

    try:
        result_json = await mcp_client.call_tool("commit_assignment", args)
        if result_json:
            result = json.loads(result_json)
            print(f"  [MCP RESPONSE] -> {result}")
            if result.get("status") == "success":
                return {"assignment_status": "ASSIGNED"}
            else:
                error_msg = result.get("message", "Unknown error")
                print(f"  [MCP ERROR from Server] -> {error_msg}")
                return {"assignment_status": "NEEDS_MANUAL_ASSIGNMENT"}
        return {"assignment_status": "NEEDS_MANUAL_ASSIGNMENT"}
    except Exception as e:
        logger.error(f"  [MCP EXCEPTION] -> {e}")
        return {"assignment_status": "NEEDS_MANUAL_ASSIGNMENT"}
