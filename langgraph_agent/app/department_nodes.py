"""
Bridges PipelineState (the master graph's shared state) to each Layer 3
department's own isolated state, and back.

Why wrapper functions instead of direct subgraph nodes: MaintenanceState and
FAQState deliberately share no keys with PipelineState (see faq/state.py's
docstring -- "nothing here is shared with any other department's state").
LangGraph's docs call this the "subgraph with a different schema" pattern:
a plain node function transforms state in, calls subgraph.ainvoke(...), and
transforms the result back out. This is the intended approach here, not a
workaround -- department isolation was a deliberate design choice upstream,
and this is what makes it work inside one parent graph.

department_router uses Command(goto=...) rather than add_conditional_edges +
a separate router function: the idiomatic LangGraph pattern for
supervisor/dispatcher nodes, since it lets one node pick the destination and
write state in a single return value. No LLM call here -- same "deterministic,
auditable routing" principle rules_engine_node already follows.
"""
import logging
from typing import Literal, Dict, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from app.pipeline_state import PipelineState
from app.checkpointer import get_checkpointer

from app.core_workflows.maintenance.graph import build_maintenance_graph
from app.core_workflows.faq.graph import build_faq_graph
from app.core_workflows.rent_renewal.graph import build_rent_renewal_graph

logger = logging.getLogger(__name__)


# --- Lazily-built, checkpointer-backed department graph instances ---
# Built once per process, using the SAME shared persistent checkpointer, so a
# paused human_approval_node interrupt (or a multi-turn FAQ/property-search
# conversation) survives a restart. Solo test files are untouched -- they
# still import maintenance_graph / faq_graph / graph directly from their own
# modules and get the default MemorySaver-backed instances.

_maintenance_graph = None
_faq_graph = None
_rent_renewal_graph = None


async def _get_maintenance_graph():
    global _maintenance_graph
    if _maintenance_graph is None:
        checkpointer = await get_checkpointer()
        _maintenance_graph = build_maintenance_graph(checkpointer=checkpointer)
    return _maintenance_graph


async def _get_faq_graph():
    global _faq_graph
    if _faq_graph is None:
        checkpointer = await get_checkpointer()
        _faq_graph = build_faq_graph(checkpointer=checkpointer)
    return _faq_graph


async def _get_rent_renewal_graph():
    global _rent_renewal_graph
    if _rent_renewal_graph is None:
        checkpointer = await get_checkpointer()
        _rent_renewal_graph = build_rent_renewal_graph(checkpointer=checkpointer)
    return _rent_renewal_graph

# --- Router ---

def department_router(state: PipelineState) -> Command[Literal["maintenance", "faq", "rent_renewal", "fallback"]]:
    """Reads Layer 2's decision and dispatches to the matching Layer 3 department."""
    response = state.get("response")
    action = response.action_taken if response else None
    intent = state.get("intent")

    if action in ("human_escalation", "needs_human_review"):
        destination = "fallback"
    elif action == "routed_to_maintenance_workflow" or intent == "maintenance":
        destination = "maintenance"
    elif action == "routed_to_faq_workflow" or intent in ("faq", "billing"):
        destination = "faq"
    elif action == "routed_to_rent_renewal_workflow" or intent in ("rent_renewal", "lease_renewal"):
        destination = "rent_renewal"
    else:
        destination = "fallback"

    logger.info(f"department_router: action={action} intent={intent} -> {destination}")
    return Command(goto=destination, update={"active_department": destination if destination != "fallback" else None})



# --- Department wrapper nodes ---

async def run_maintenance(state: PipelineState, config: RunnableConfig) -> Dict[str, Any]:
    request = state["request"]
    sub_graph = await _get_maintenance_graph()

    # Build the sub_input starting with the new user message.
    sub_input: Dict[str, Any] = {
        "messages": [HumanMessage(content=request.raw_text)],
        "user_id": request.user_id,
    }

    # On follow-up turns (active_department == "maintenance"), carry over every
    # slot that was already extracted in a previous turn.
    prev = state.get("department_result") or {}
    for slot in [
        "tenant_identity", "property_unit", "issue_category",
        "issue_description", "urgency", "permission_to_enter",
        "pets_present", "db_tenant_id", "db_unit_id",
        "ticket_payload", "created_ticket_id", "missing_slots",
    ]:
        if prev.get(slot) is not None:
            sub_input[slot] = prev[slot]

    result = await sub_graph.ainvoke(sub_input, config)

    is_complete = (
        bool(result.get("escalation_record"))
        or bool(result.get("created_ticket_id") and result.get("assignment_status"))
        or result.get("ticket_creation_status") == "error"
    )
    active_dept = None if is_complete else "maintenance"

    return {
        "active_department": active_dept,
        "department_result": None if is_complete else result,
        "final_response": result.get("final_response")
        or "Your maintenance request has been logged and is being reviewed.",
    }



async def run_faq(state: PipelineState, config: RunnableConfig) -> Dict[str, Any]:
    request = state["request"]
    sub_graph = await _get_faq_graph()

    sub_input = {
        "messages": [HumanMessage(content=request.raw_text)],
        "user_id": request.user_id,
        "session_id": request.channel_metadata.get("session_id", request.user_id),
        "user_query": request.raw_text,
        "rag_context": [],
        "escalate": False,
        "property_filters": {},
        "missing_property_fields": [],
    }
    result = await sub_graph.ainvoke(sub_input, config)

    # FAQ answers are always single-turn -- clear active_department after responding.
    final_response = result.get("final_response") or "Let me get back to you on that shortly."
    return {
        "active_department": None,
        "department_result": result,
        "final_response": final_response,
    }


async def run_rent_renewal(state: PipelineState, config: RunnableConfig) -> Dict[str, Any]:
    request = state["request"]
    sub_graph = await _get_rent_renewal_graph()

    sub_input = {
        "messages": [HumanMessage(content=request.raw_text)],
        "user_id": request.user_id,
    }
    result = await sub_graph.ainvoke(sub_input, config)

    is_complete = result.get("is_complete", True)
    active_dept = None if is_complete else "rent_renewal"
    return {
        "active_department": active_dept,
        "department_result": result,
        "final_response": "Thank you for inquiring about your rent renewal. Our team will present your options shortly.",
    }


def fallback_node(state: PipelineState) -> Dict[str, Any]:
    """Catches leasing / general / anything with no built department yet --
    same honest behaviour as rules_engine_node's own general_inquiry branch,
    just surfaced through the master graph instead of dead-ending silently."""
    response = state.get("response")
    msg = (
        response.response_message
        if response
        else "Thanks for reaching out -- a member of our team will follow up shortly."
    )
    return {"active_department": None, "final_response": msg}
