from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.orchestrator.maintenance.state import MaintenanceState
from app.orchestrator.maintenance.nodes import (
    receptionist_node,
    issue_collection_node,
    validation_node,
    priority_detection_node,
    escalation_node,
    request_builder_node,
    ticket_creation_node,
    vendor_matching_node,
    human_approval_node,
    vendor_assignment_node,
    response_generator_node
)

def priority_router(state: MaintenanceState):
    if state.get("urgency") == "EMERGENCY":
        return "escalation"
    return "validation"

def validation_router(state: MaintenanceState):
    if state.get("missing_slots"):
        return "ask_user"
    return "request_builder"

def build_maintenance_graph(checkpointer=None):
    """
    Factory instead of a module-level singleton so the checkpointer is injectable:
    solo/dev testing gets a fresh in-memory MemorySaver by default (unchanged
    behaviour for existing test_maintenance_stage*.py files), while the production
    pipeline (app/pipeline.py) passes in the one shared, persistent checkpointer so
    human_approval_node's interrupt() survives a process restart instead of being
    lost with it.
    """
    workflow = StateGraph(MaintenanceState)

    workflow.add_node("receptionist", receptionist_node)
    workflow.add_node("issue_collection", issue_collection_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("priority_detection", priority_detection_node)
    workflow.add_node("escalation", escalation_node)
    workflow.add_node("request_builder", request_builder_node)
    workflow.add_node("ticket_creation", ticket_creation_node)
    workflow.add_node("vendor_matching", vendor_matching_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("vendor_assignment", vendor_assignment_node)
    workflow.add_node("response_generator", response_generator_node)

    # Node Sequence:
    # Receptionist Node -> Issue Collection Node -> Priority Detection Node
    workflow.add_edge(START, "receptionist")
    workflow.add_edge("receptionist", "issue_collection")
    workflow.add_edge("issue_collection", "priority_detection")

    # Priority Detection Node -> Escalation Node (if EMERGENCY) else Validation Node
    workflow.add_conditional_edges(
        "priority_detection",
        priority_router,
        {
            "escalation": "escalation",
            "validation": "validation"
        }
    )

    # Validation Node -> Request Builder Node (if complete) OR END (if asking user)
    workflow.add_conditional_edges(
        "validation",
        validation_router,
        {
            "ask_user": END,
            "request_builder": "request_builder"
        }
    )

    workflow.add_edge("escalation", END)

    # Request Builder Node -> ticket creation step -> Vendor Assignment Pipeline -> Response Generator -> END
    workflow.add_edge("request_builder", "ticket_creation")
    workflow.add_edge("ticket_creation", "vendor_matching")
    workflow.add_edge("vendor_matching", "human_approval")
    workflow.add_edge("human_approval", "vendor_assignment")
    workflow.add_edge("vendor_assignment", "response_generator")
    workflow.add_edge("response_generator", END)

    return workflow.compile(checkpointer=checkpointer or MemorySaver())


# Default instance -- used by existing solo test files exactly as before (test_maintenance_stage1.py etc.),
# each gets its own fresh MemorySaver. The production pipeline builds its own instance via
# build_maintenance_graph(checkpointer=<shared persistent checkpointer>) instead of using this one.
maintenance_graph = build_maintenance_graph()
