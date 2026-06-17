import logging
from typing import Literal, Dict, Any

from langgraph.graph import StateGraph, END

from app.state import ConversationState
from app.nodes.intent_node import intent_node
from app.nodes.property_search_node import property_search_node
from app.nodes.response_formatter_node import response_formatter_node

logger = logging.getLogger(__name__)

def route_intent(state: Dict[str, Any]) -> str:
    """
    Route from intent_node based on the state.
    
    If all information is complete, intent_node sets next_step to "property_search".
    If we are missing information, we route to END to wait for user input
    (which practically "returns to intent_node" on the next graph execution).
    """
    next_step = state.get("next_step")
    
    if next_step == "property_search":
        return "property_search_node"
    
    return END

def build_graph():
    """
    Build and compile the LangGraph workflow for the Real Estate Voice Agent.
    """
    workflow = StateGraph(ConversationState)
    
    # 1. Register existing nodes
    workflow.add_node("intent_node", intent_node)
    workflow.add_node("property_search_node", property_search_node)
    workflow.add_node("response_formatter_node", response_formatter_node)
    
    # 2. Entry Point
    workflow.set_entry_point("intent_node")
    
    # 3. Create conditional routing
    workflow.add_conditional_edges(
        "intent_node",
        route_intent,
        {
            "property_search_node": "property_search_node",
            END: END
        }
    )
    
    # 4. After property_search_node, route to response_formatter_node
    workflow.add_edge("property_search_node", "response_formatter_node")
    
    # 5. After response_formatter_node, route to END
    workflow.add_edge("response_formatter_node", END)
    
    # 6. Compile graph
    return workflow.compile()

graph = build_graph()
