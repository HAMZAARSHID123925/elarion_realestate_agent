import json
import logging
from typing import Dict, Any

from app.core_workflows.maintenance.state import MaintenanceState
from app.core_workflows.maintenance.mcp_client import mcp_client

logger = logging.getLogger(__name__)


async def receptionist_node(state: MaintenanceState) -> Dict[str, Any]:
    """Tenant lookup over MCP. Stores display identity + real DB IDs."""
    updates = {}

    # If already fully identified in DB, skip
    if state.get("db_tenant_id") and state.get("db_unit_id"):
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
                logger.info(f"Receptionist: Unknown phone {user_id}. {result.get('error')}")

    # Secondary lookup: if phone lookup failed but user typed their name in chat
    tenant_identity = state.get("tenant_identity")
    if not updates.get("db_tenant_id") and tenant_identity:
        try:
            result_json = await mcp_client.call_tool("lookup_tenant_by_name", {"name": tenant_identity})
            if result_json:
                result = json.loads(result_json)
                if "error" not in result:
                    updates["tenant_identity"] = result.get("name") or tenant_identity
                    updates["property_unit"] = result.get("unit_id")
                    updates["db_tenant_id"] = result.get("tenant_id")
                    updates["db_unit_id"] = result.get("unit_id")
                    logger.info(f"Receptionist: Found tenant by name {tenant_identity} -> {updates['db_tenant_id']}")
        except Exception as e:
            logger.error(f"Receptionist: Name lookup failed for {tenant_identity}: {e}")

    return updates

