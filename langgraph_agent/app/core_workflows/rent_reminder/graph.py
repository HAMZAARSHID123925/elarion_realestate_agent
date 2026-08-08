"""
Rent Reminder & Human Escalation Subgraph Construction.
"""
from langgraph.graph import StateGraph, START, END

from app.core_workflows.rent_reminder.state import RentReminderState
from app.core_workflows.rent_reminder.nodes import (
    payment_check_node,
    reminder_decision_node,
    reminder_send_node,
    followup_tracker_node,
    human_escalation_node,
)

def route_reminder_decision(state: RentReminderState) -> str:
    """Conditional routing function based on decision node action output."""
    action = state.get("action", "SKIP")
    if action in ("SEND_REMINDER", "SEND_FOLLOWUP"):
        return "reminder_send"
    elif action == "ESCALATE":
        return "human_escalation"
    else:
        return "end"

def build_rent_reminder_graph(checkpointer=None):
    """
    Builds and compiles the Rent Reminder & Escalation LangGraph Subgraph.
    """
    builder = StateGraph(RentReminderState)

    # Add nodes
    builder.add_node("payment_check", payment_check_node)
    builder.add_node("reminder_decision", reminder_decision_node)
    builder.add_node("reminder_send", reminder_send_node)
    builder.add_node("followup_tracker", followup_tracker_node)
    builder.add_node("human_escalation", human_escalation_node)

    # Add linear start edges
    builder.add_edge(START, "payment_check")
    builder.add_edge("payment_check", "reminder_decision")

    # Add conditional edge from decision node
    builder.add_conditional_edges(
        "reminder_decision",
        route_reminder_decision,
        {
            "reminder_send": "reminder_send",
            "human_escalation": "human_escalation",
            "end": END
        }
    )

    # Add downstream completion edges
    builder.add_edge("reminder_send", "followup_tracker")
    builder.add_edge("followup_tracker", END)
    builder.add_edge("human_escalation", END)

    return builder.compile(checkpointer=checkpointer)

rent_reminder_graph = build_rent_reminder_graph()
