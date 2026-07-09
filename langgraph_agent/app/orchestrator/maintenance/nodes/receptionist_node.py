import json
import logging
from typing import Dict, Any

from app.orchestrator.maintenance.state import MaintenanceState
from app.orchestrator.maintenance.mcp_client import mcp_client

logger = logging.getLogger(__name__)


async def receptionist_node(state: MaintenanceState) -> Dict[str, Any]:
    """Tenant lookup over MCP. Stores display identity + real DB IDs."""
    updates = {}

    # If already identified, skip
    if state.get("tenant_identity") and state.get("property_unit"):
        return updates

    user_id = state.get("user_id")
    if user_id:
        result_json = await mcp_client.call_tool("lookup_tenant", {"phone_or_email": user_id})
        if result_json:
            result = json.loads(result_json)
            if "error" not in result:
                updates["tenant_identity"] = result.get("name")         # display name for conversation
                updates["property_unit"] = result.get("unit_id")        # unit label
                updates["db_tenant_id"] = result.get("tenant_id")       # real DB FK
                updates["db_unit_id"] = result.get("unit_id")           # real DB FK
                logger.info(f"Receptionist: Found tenant {updates['tenant_identity']} "
                            f"(id={updates['db_tenant_id']}) in {updates['property_unit']}")
            else:
                logger.info(f"Receptionist: Unknown tenant. {result.get('error')}")
    else:
        logger.info("Receptionist: No user_id provided.")

    return updates
