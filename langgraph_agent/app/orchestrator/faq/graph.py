"""
FAQ / Workflow #3 graph -- Tenant Support & FAQ Automation.

Wires the 8 nodes from design doc section 7.2 using the conditional edges from
section 7.3, plus one continuation the table doesn't spell out explicitly but
the section 3 flow diagram requires: MIXED must run the Knowledge path AND the
Property path before compose_response, not just one of them.

Routing after classify_intent is all plain Python router functions (design doc
section 7.3: "deterministic Python, matching the project's rule of keeping the
rules engine as plain conditionals, not LLM calls, for auditability and latency")
-- same pattern as maintenance/graph.py's priority_router / validation_router.

Compiled with a MemorySaver checkpointer keyed by session_id, so multi-turn
slot accumulation (design doc section 7.4) works the same way maintenance's
checkpointer does.
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.orchestrator.faq.state import FAQState
from app.orchestrator.faq.nodes.classify_intent_node import classify_intent_node
from app.orchestrator.faq.nodes.rag_retrieve_node import rag_retrieve_node
from app.orchestrator.faq.nodes.rag_generate_node import rag_generate_node
from app.orchestrator.faq.nodes.collect_property_slots_node import collect_property_slots_node
from app.orchestrator.faq.nodes.call_property_mcp_node import call_property_mcp_node
from app.orchestrator.faq.nodes.recommend_generate_node import recommend_generate_node
from app.orchestrator.faq.nodes.clarify_node import clarify_node
from app.orchestrator.faq.nodes.compose_response_node import compose_response_node


# --- Router functions (design doc section 7.3 table) ---

def intent_router(state: FAQState) -> str:
    intent = state.get("intent")
    if intent in ("KNOWLEDGE", "MIXED"):
        return "rag_retrieve"
    if intent == "PROPERTY":
        return "collect_property_slots"
    return "clarify"  # UNCLEAR


def confidence_router(state: FAQState) -> str:
    if state.get("escalate"):
        return "compose_response"
    return "rag_generate"


def mixed_continuation_router(state: FAQState) -> str:
    # After the knowledge answer is generated: MIXED keeps going into the
    # property path; plain KNOWLEDGE is done and goes straight to compose.
    if state.get("intent") == "MIXED":
        return "collect_property_slots"
    return "compose_response"


def slots_router(state: FAQState) -> str:
    if state.get("missing_property_fields"):
        return "clarify"
    return "call_property_mcp"


def build_faq_graph(checkpointer=None):
    """
    checkpointer is injectable for the same reason as build_maintenance_graph:
    defaults to a fresh MemorySaver for solo/dev testing (existing test_faq_stage1.py
    keeps working unchanged), while app/pipeline.py passes in the shared, persistent
    checkpointer for production so multi-turn slot accumulation survives a restart.
    """
    workflow = StateGraph(FAQState)

    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("rag_retrieve", rag_retrieve_node)
    workflow.add_node("rag_generate", rag_generate_node)
    workflow.add_node("collect_property_slots", collect_property_slots_node)
    workflow.add_node("call_property_mcp", call_property_mcp_node)
    workflow.add_node("recommend_generate", recommend_generate_node)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("compose_response", compose_response_node)

    workflow.add_edge(START, "classify_intent")

    workflow.add_conditional_edges(
        "classify_intent",
        intent_router,
        {
            "rag_retrieve": "rag_retrieve",
            "collect_property_slots": "collect_property_slots",
            "clarify": "clarify",
        },
    )

    workflow.add_conditional_edges(
        "rag_retrieve",
        confidence_router,
        {
            "compose_response": "compose_response",
            "rag_generate": "rag_generate",
        },
    )

    workflow.add_conditional_edges(
        "rag_generate",
        mixed_continuation_router,
        {
            "collect_property_slots": "collect_property_slots",
            "compose_response": "compose_response",
        },
    )

    workflow.add_conditional_edges(
        "collect_property_slots",
        slots_router,
        {
            "clarify": "clarify",
            "call_property_mcp": "call_property_mcp",
        },
    )

    workflow.add_edge("call_property_mcp", "recommend_generate")
    workflow.add_edge("recommend_generate", "compose_response")
    workflow.add_edge("clarify", "compose_response")
    workflow.add_edge("compose_response", END)

    return workflow.compile(checkpointer=checkpointer or MemorySaver())


faq_graph = build_faq_graph()
