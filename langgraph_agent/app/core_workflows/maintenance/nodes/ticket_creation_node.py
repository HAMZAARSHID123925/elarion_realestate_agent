import json
import logging
import uuid
from typing import Dict, Any

from app.core_workflows.maintenance.state import MaintenanceState
from app.core_workflows.maintenance.mcp_client import mcp_client

logger = logging.getLogger(__name__)


async def ticket_creation_node(state: MaintenanceState) -> Dict[str, Any]:
    """Calls MCP server to create ticket."""
    payload = state.get("ticket_payload", {})

    # Fail closed: never send an unresolved tenant/unit to Postgres as a foreign key.
    # request_builder_node only sets these when a real DB lookup succeeded, so None here
    # means the tenant could not be verified -- stop before the DB call, don't guess.
    if not payload.get("tenant_id") or not payload.get("unit_id"):
        error_msg = "Could not verify tenant/unit against records; ticket not created."
        logger.warning(
            f"[TICKET CREATION] -> Skipping DB call, unresolved identity: "
            f"tenant_id={payload.get('tenant_id')} unit_id={payload.get('unit_id')}"
        )
        return {"ticket_creation_status": "error", "ticket_creation_error": error_msg}

    # Generate client-side idempotency key
    idempotency_key = f"idem-{uuid.uuid4()}"

    # Map payload to MCP tool arguments
    args = {
        "tenant_id": payload.get("tenant_id") or "UNKNOWN",
        "unit_id": payload.get("unit_id") or "UNKNOWN",
        "category": payload.get("category") or "general",
        "description": payload.get("description") or "",
        "urgency": payload.get("urgency") or "low",
        "permission_to_enter": payload.get("permission_to_enter") or "unconfirmed",
        "pets_present": payload.get("pets_present") or "unconfirmed",
        "idempotency_key": idempotency_key
    }

    print(f"\n[TICKET CREATION] -> Calling MCP create_ticket with args: {args}")

    try:
        result_json = await mcp_client.call_tool("create_ticket", args)
        if result_json:
            result = json.loads(result_json)
            print(f"  [MCP RESPONSE] -> {result}")
            if result.get("status") in ["success", "duplicate"]:
                ticket = result.get("ticket", {})
                out = {"ticket_creation_status": "success", "ticket_creation_error": None}
                # Carry ticket_id + property_id forward so downstream vendor matching
                # doesn't have to re-derive them.
                created_ticket_id = ticket.get("ticket_id") or result.get("existing_ticket_id")
                if created_ticket_id:
                    out["created_ticket_id"] = created_ticket_id
                if ticket.get("property_id"):
                    out["db_property_id"] = ticket.get("property_id")
                return out
            else:
                error_msg = result.get("message") or result.get("error") or "Unknown error"
                print(f"  [MCP ERROR from Server] -> {error_msg}")
                return {"ticket_creation_status": "error", "ticket_creation_error": error_msg}
        else:
            return {"ticket_creation_status": "error", "ticket_creation_error": "Empty response"}
    except Exception as e:
        logger.error(f"  [MCP EXCEPTION] -> {e}")
        return {"ticket_creation_status": "error", "ticket_creation_error": str(e)}
