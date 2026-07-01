import logging
from langgraph.graph import StateGraph, END

from app.orchestrator.state import OrchestratorState
from app.orchestrator.nodes import (
    identification_node,
    classify_and_extract_node,
    rules_engine_node
)

logger = logging.getLogger(__name__)

def build_orchestrator_graph():
    """
    Builds the Layer 2 Orchestrator Graph.
    Refactored for Production: Reduced nodes for lower latency and async execution.
    """
    workflow = StateGraph(OrchestratorState)
    
    # 1. Register Nodes
    workflow.add_node("identification", identification_node)
    workflow.add_node("classify_and_extract", classify_and_extract_node)
    workflow.add_node("rules_engine", rules_engine_node)
    
    # 2. Define Entry Point
    workflow.set_entry_point("identification")
    
    # 3. Define Edges (The Flow)
    # After identifying the user, we classify intent, urgency, and extract entities in one call
    workflow.add_edge("identification", "classify_and_extract")
    
    # Run the rules engine to decide the action based on extracted data
    workflow.add_edge("classify_and_extract", "rules_engine")
    
    # Rules engine outputs the UnifiedResponse object for Layer 3
    workflow.add_edge("rules_engine", END)
    
    # 4. Compile Graph
    return workflow.compile()

# Export the compiled graph
orchestrator_graph = build_orchestrator_graph()
