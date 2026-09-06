import json
import logging
import re
from typing import Dict, Any

from app.core_workflows.maintenance.state import MaintenanceState
from app.core_workflows.maintenance.mcp_client import mcp_client

logger = logging.getLogger(__name__)


async def receptionist_node(state: MaintenanceState) -> Dict[str, Any]:
    """Tenant lookup over MCP. Stores display identity + real DB IDs.

    Resolution order:
    1. Primary   - lookup_tenant(phone_or_email=user_id)    [WhatsApp / registered email]
    2. Secondary - lookup_tenant_by_name(name)              [user said their name in chat]
    3. Tertiary  - lookup_tenant_by_unit(unit_id)           [unit from state (multi-turn carry-over)]
    4. Quaternary- lookup_tenant_by_unit(extracted_unit)    [unit extracted from raw message text]
       This fourth step is the critical fix for email-channel users whose email address
       is not registered in the DB: they often mention their unit in the first message
       (e.g. "my AC is broken in Unit 204"), so we extract it and look them up by unit.
    """
    updates = {}

    # If already fully identified in DB, skip
    if state.get("db_tenant_id") and state.get("db_unit_id"):
        return updates

    user_id = state.get("user_id")
    if user_id:
        try:
            result_json = await mcp_client.call_tool("lookup_tenant", {"phone_or_email": user_id})
            if result_json:
                result = json.loads(result_json) if isinstance(result_json, str) else result_json
                if "error" not in result:
                    updates["tenant_identity"] = result.get("name")         # display name for conversation
                    updates["property_unit"] = result.get("unit_id")        # unit label
                    updates["db_tenant_id"] = result.get("tenant_id")       # real DB FK
                    updates["db_unit_id"] = result.get("unit_id")           # real DB FK
                    logger.info(
                        f"Receptionist: Found tenant {updates['tenant_identity']} "
                        f"(id={updates['db_tenant_id']}) in {updates['property_unit']}"
                    )
                else:
                    logger.info(f"Receptionist: Unknown contact {user_id!r}. {result.get('error')}")
        except Exception as e:
            logger.error(f"Receptionist: Primary lookup failed for {user_id}: {e}")

    # Secondary lookup: if phone/email lookup failed but user typed their name in chat
    tenant_identity = state.get("tenant_identity")
    if not updates.get("db_tenant_id") and tenant_identity:
        try:
            result_json = await mcp_client.call_tool("lookup_tenant_by_name", {"name": tenant_identity})
            if result_json:
                result = json.loads(result_json) if isinstance(result_json, str) else result_json
                if "error" not in result:
                    updates["tenant_identity"] = result.get("name") or tenant_identity
                    updates["property_unit"] = result.get("unit_id")
                    updates["db_tenant_id"] = result.get("tenant_id")
                    updates["db_unit_id"] = result.get("unit_id")
                    logger.info(f"Receptionist: Found tenant by name {tenant_identity!r} -> {updates['db_tenant_id']}")
        except Exception as e:
            logger.error(f"Receptionist: Name lookup failed for {tenant_identity}: {e}")

    # Tertiary lookup: if unit is already provided in state (e.g. from multi-turn carry-over)
    property_unit = updates.get("property_unit") or state.get("property_unit")

    # Quaternary: extract unit from the raw message text on the FIRST turn.
    # This handles email / WhatsApp users who mention their unit in the message body
    # but whose contact info is not in the DB (e.g. a Gmail address vs a stored phone number).
    if not property_unit:
        messages = state.get("messages", [])
        raw_text = messages[-1].content if messages and hasattr(messages[-1], "content") else ""
        # Matches: "Unit 204", "unit204", "U-204", "Apt 4B", "#204", "apartment 12", etc.
        unit_match = re.search(
            r'\b(?:unit|apt|apartment|flat|house|u)[\s.\-#]*(\w+)\b'
            r'|\b#(\d+\w*)\b',
            raw_text, re.IGNORECASE
        )
        if unit_match:
            extracted = next((g for g in unit_match.groups() if g), None)
            if extracted:
                property_unit = extracted.strip()
                logger.info(f"Receptionist: Extracted unit from message text: {property_unit!r}")

    if not updates.get("db_unit_id") and property_unit:
        try:
            result_json = await mcp_client.call_tool("lookup_tenant_by_unit", {"unit_id": property_unit})
            if result_json:
                result = json.loads(result_json) if isinstance(result_json, str) else result_json
                if "error" not in result:
                    updates["tenant_identity"] = updates.get("tenant_identity") or result.get("name")
                    updates["property_unit"] = result.get("unit_id")
                    updates["db_tenant_id"] = updates.get("db_tenant_id") or result.get("tenant_id")
                    updates["db_unit_id"] = result.get("unit_id")
                    logger.info(
                        f"Receptionist: Resolved tenant by unit {property_unit!r} -> "
                        f"tenant={updates['db_tenant_id']}, unit={updates['db_unit_id']}"
                    )
                else:
                    logger.info(f"Receptionist: Unit {property_unit!r} not found in DB. Continuing as guest.")
        except Exception as e:
            logger.error(f"Receptionist: Unit lookup failed for {property_unit}: {e}")

    return updates
