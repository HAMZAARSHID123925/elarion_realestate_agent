import json
import logging
from typing import Dict, Any

from app.core_workflows.maintenance.state import MaintenanceState
from app.core_workflows.maintenance.mcp_client import mcp_client

logger = logging.getLogger(__name__)

async def request_builder_node(state: MaintenanceState) -> Dict[str, Any]:
    """Assembles validated slots into payload."""
    db_tenant_id = state.get("db_tenant_id")
    db_unit_id = state.get("db_unit_id")
    tenant_identity = state.get("tenant_identity")
    
    # If we didn't identify them at the start but got their name/unit during chat, try to resolve it now
    # to avoid PostgreSQL foreign key constraint errors
    if not db_tenant_id and tenant_identity:
        try:
            # 1. Try to lookup by exact name
            result_json = await mcp_client.call_tool("lookup_tenant_by_name", {"name": tenant_identity})
            result = json.loads(result_json) if result_json else {}
            
            # 2. If name was misspelled (Jhon vs John), fallback to looking up whoever lives in that unit
            if "error" in result and state.get("property_unit"):
                result_json = await mcp_client.call_tool("lookup_tenant_by_unit", {"unit_id": state.get("property_unit")})
                result = json.loads(result_json) if result_json else {}
                
            if "error" not in result:
                db_tenant_id = result.get("tenant_id")
                db_unit_id = result.get("unit_id")
                logger.info(f"Resolved tenant for {tenant_identity}/{state.get('property_unit')} -> {db_tenant_id}")
            else:
                logger.warning(f"Could not resolve tenant ID for {tenant_identity} / {state.get('property_unit')}")
        except Exception as e:
            logger.error(f"Failed to resolve tenant: {e}")

    payload = {
        # Only ever use resolved DB IDs here -- tenant_identity/property_unit are raw
        # conversational text (e.g. a typed name), not valid foreign keys. If db_tenant_id/
        # db_unit_id are still None at this point, ticket_creation_node fails closed instead
        # of sending unresolved text to Postgres as a foreign key.
        "tenant_id": db_tenant_id,
        "unit_id": db_unit_id,
        "category": state.get("issue_category"),
        "description": state.get("issue_description"),
        "urgency": state.get("urgency"),
        "permission_to_enter": state.get("permission_to_enter"),
        "pets_present": state.get("pets_present")
    }
    
    # Return updated db IDs as well so downstream nodes have them
    return {
        "ticket_payload": payload,
        "db_tenant_id": db_tenant_id,
        "db_unit_id": db_unit_id
    }
