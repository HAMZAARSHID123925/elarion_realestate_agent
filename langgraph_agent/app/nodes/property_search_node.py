# import logging
# from typing import Dict, Any

# logger = logging.getLogger(__name__)

# def property_search_node(state: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Property Search Node
    
#     1. Responsibilities:
#        - Receive state from the Receptionist Node.
#        - Validate that all required fields exist (user_name, location, budget, property_type).
#        - If any field is missing, return control back to the Receptionist Node.
#        - If all fields exist, prepare a structured payload for the future MCP server.
#        - Does NOT execute property search, call MCP, or generate database queries.
       
#     2. Input State:
#        - user_name: The user's name.
#        - location: The desired city/location.
#        - budget: The budget for the property.
#        - property_type: The type of property (e.g., house, apartment).
       
#     3. Output State:
#        - property_search_request: A dictionary payload of the search parameters (only if complete).
#        - next_step: Routing instruction ("mcp_search" if complete, "intent_node" if incomplete).
       
#     4. Decision Logic:
#        - Checks the state dictionary for the existence of all 4 required keys.
#        - If any key is missing or None, sets next_step="intent_node" to bounce back.
#        - If all keys exist, creates the payload dict, stores it in property_search_request,
#          and routes to the next phase with next_step="mcp_search".
#     """
#     required_fields = ["user_name", "location", "budget", "property_type"]
    
#     # 2. Validate all required fields exist
#     missing = [field for field in required_fields if not state.get(field)]
    
#     if missing:
#         # 3. If any field is missing, return control back to Receptionist Node (intent_node)
#         logger.warning(f"Property search node invoked with missing fields: {missing}. Returning to receptionist.")
#         return {"next_step": "intent_node"}
        
#     # 4. If all fields exist, create a structured payload
#     payload = {
#         "user_name": state.get("user_name"),
#         "location": state.get("location"),
#         "budget": state.get("budget"),
#         "property_type": state.get("property_type")
#     }
    
#     # Store payload and set next_step
#     return {
#         "property_search_request": payload,
#         "next_step": "mcp_search"
#     }









import logging
import sys
import os
from typing import Dict, Any

# Add root to path so we can import the MCP server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from mcp_servers.property_search.server import search_properties

logger = logging.getLogger(__name__)

def property_search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Property Search Node — calls the MCP server directly.
    """
    required_fields = ["user_name", "location", "budget", "property_type"]
    missing = [field for field in required_fields if not state.get(field)]

    if missing:
        logger.warning(f"Missing fields: {missing}. Routing back to intent_node.")
        return {"next_step": "intent_node"}

    location = state.get("location")
    budget = state.get("budget")
    property_type = state.get("property_type")
    user_name = state.get("user_name")

    logger.info(f"Searching for {user_name}: {property_type} in {location}, budget {budget}")

    try:
        result = search_properties(
            location=location,
            property_type=property_type,
            budget=budget
        )

        return {
            "property_search_result": result,
            "is_conversation_complete": True,
            "next_step": "complete"
        }

    except Exception as e:
        logger.error(f"MCP call failed: {e}")
        return {
            "property_search_result": {
                "status": "error",
                "message": "Property search is currently unavailable. Please try again."
            },
            "is_conversation_complete": True,
            "next_step": "complete"
        }