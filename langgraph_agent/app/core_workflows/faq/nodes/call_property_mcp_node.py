"""
call_property_mcp_node -- design doc section 5 / 7.2.

Only reached once collect_property_slots_node confirms the required filters
are complete. Calls the existing property_search MCP server -- this is the
"source of truth" (design doc section 1); this node never touches the vector DB.
"""
import json
import logging
from app.core_workflows.faq.state import FAQState
from app.core_workflows.faq.mcp_client import property_mcp_client

logger = logging.getLogger(__name__)


async def call_property_mcp_node(state: FAQState) -> dict:
    filters = state.get("property_filters", {})

    await property_mcp_client.connect()

    mcp_args = {
        "location": filters.get("location", ""),
        "property_type": filters.get("property_type", ""),
        "budget": filters.get("budget", ""),
    }
    if filters.get("bedrooms") is not None:
        mcp_args["bedrooms"] = filters["bedrooms"]

    raw_result = await property_mcp_client.call_tool("search_properties", mcp_args)

    try:
        result = json.loads(raw_result) if raw_result else {"status": "error", "properties": [], "count": 0}
    except (json.JSONDecodeError, TypeError):
        result = {"status": "error", "message": "Could not parse MCP response", "properties": [], "count": 0}

    logger.info(f"[FAQ] MCP search returned status={result.get('status')} count={result.get('count')}")

    return {"mcp_results": result}
