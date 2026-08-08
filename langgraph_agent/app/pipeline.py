"""
The master Elarion pipeline -- the missing piece that turns three
independently-tested graphs (Workflow 1, the Layer 2 orchestrator, and the
Layer 3 maintenance/FAQ subgraphs) into one production system.

Structure, per LangGraph's subgraph guidance:
  - orchestrator_graph is added DIRECTLY as a node (`add_node("orchestrator",
    orchestrator_graph)`) because PipelineState is a superset of
    OrchestratorState -- LangGraph maps the shared keys automatically on entry
    and merges them back on exit. No wrapper needed.
  - maintenance / faq / property_search are invoked through thin wrapper nodes
    (app/department_nodes.py) instead, because their state schemas are
    deliberately isolated and share no keys with PipelineState.
  - department_router uses Command(goto=...) to pick the destination in one
    step -- the idiomatic LangGraph pattern for supervisor/dispatcher nodes.
  - The whole graph is compiled with ONE persistent checkpointer
    (app/checkpointer.py). This is what makes maintenance's human_approval_node
    interrupt() survive a process restart instead of losing the paused ticket.

handle_request() is the single production entry point every channel adapter
should call -- VAPI today, WhatsApp/Email/SMS later. Nothing about this file
needs to change when a new channel is added; only a new adapter that also
calls handle_request() is needed.
"""
import logging
from typing import Dict, Any, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from app.pipeline_state import PipelineState
from app.orchestrator.graph import orchestrator_graph
from app.orchestrator.schemas import UnifiedRequest
from app.checkpointer import get_checkpointer
from app.department_nodes import (
    department_router,
    run_maintenance,
    run_faq,
    run_rent_renewal,
    run_rent_reminder,
    fallback_node,
)

logger = logging.getLogger(__name__)


def compose_response(state: PipelineState) -> Dict[str, Any]:
    """Last stop before handing control back to the channel adapter --
    normalizes whichever department ran into a single response string."""
    return {
        "final_response": state.get("final_response")
        or "I'm sorry, I couldn't process that. Could you try again?"
    }


def entry_router(state: PipelineState) -> str:
    """
    Routes active department workflows (e.g. maintenance slot-filling) directly back to 
    the active department so short follow-up answers (names, units, yes/no) aren't misclassified 
    by Layer 2, while allowing clear emergencies or FAQ switches to route back to the Orchestrator.
    """
    active = state.get("active_department")
    if active in ["maintenance", "rent_renewal"]:
        request = state.get("request")
        raw_text = (request.raw_text if request else "").lower().strip()
        
        # Check if the user is raising an emergency or asking an explicit FAQ question
        faq_keywords = ["policy", "pet", "hours", "rent payment", "deposit", "rules", "billing", "how do i pay"]
        emergency_keywords = ["gas smell", "gas leak", "active flooding", "fire", "burst", "smoke", "carbon monoxide", "no heat"]
        
        is_faq_switch = any(kw in raw_text for kw in faq_keywords)
        is_emergency_switch = any(kw in raw_text for kw in emergency_keywords)
        
        if not is_faq_switch and not is_emergency_switch:
            logger.info(f"entry_router: Resuming active workflow for department: {active}")
            return active
            
    return "orchestrator"



def build_pipeline_graph() -> StateGraph:
    workflow = StateGraph(PipelineState)

    workflow.add_node("orchestrator", orchestrator_graph)
    workflow.add_node("department_router", department_router)
    workflow.add_node("maintenance", run_maintenance)
    workflow.add_node("faq", run_faq)
    workflow.add_node("rent_renewal", run_rent_renewal)
    workflow.add_node("rent_reminder", run_rent_reminder)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("compose_response", compose_response)

    workflow.add_conditional_edges(
        START,
        entry_router,
        {
            "orchestrator": "orchestrator",
            "maintenance": "maintenance",
            "faq": "faq",
            "rent_renewal": "rent_renewal"
        }
    )
    workflow.add_edge("orchestrator", "department_router")
    # department_router returns Command(goto=...) at runtime -- its possible
    # destinations are declared via the Command[Literal[...]] return type in
    # department_nodes.py, so no add_conditional_edges mapping is needed here.
    workflow.add_edge("maintenance", "compose_response")
    workflow.add_edge("faq", "compose_response")
    workflow.add_edge("rent_renewal", "compose_response")
    workflow.add_edge("rent_reminder", "compose_response")
    workflow.add_edge("fallback", "compose_response")
    workflow.add_edge("compose_response", END)

    return workflow


_compiled_graph = None


async def get_pipeline_graph():
    """Compiles the master graph once per process, wired to the shared
    persistent checkpointer."""
    global _compiled_graph
    if _compiled_graph is None:
        checkpointer = await get_checkpointer()
        _compiled_graph = build_pipeline_graph().compile(checkpointer=checkpointer)
        logger.info("Master pipeline graph compiled")
    return _compiled_graph


async def invoke_pipeline(
    channel: str,
    user_id: str,
    raw_text: str,
    channel_metadata: Optional[Dict[str, Any]] = None,
) -> tuple[Dict[str, Any], RunnableConfig]:
    graph = await get_pipeline_graph()
    request = UnifiedRequest(
        channel=channel,
        user_id=user_id,
        raw_text=raw_text,
        channel_metadata=channel_metadata or {},
    )
    # thread_id keys the whole conversation (across Layer 2 AND whichever
    # department subgraph runs) to this specific person on this specific
    # channel -- this is what "continuing a conversation" means to the
    # checkpointer.
    config = {"configurable": {"thread_id": f"{channel}:{user_id}"}}

    result = await graph.ainvoke({"request": request}, config)
    return result, config


async def resume_pipeline(config: RunnableConfig, resume_value: Any) -> tuple[Dict[str, Any], RunnableConfig]:
    graph = await get_pipeline_graph()
    result = await graph.ainvoke(Command(resume=resume_value), config)
    return result, config


async def handle_request(
    channel: str,
    user_id: str,
    raw_text: str,
    channel_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    The single production entry point for every channel adapter.

    channel:          "vapi" | "whatsapp" | "email" | "sms" | ...
    user_id:           caller phone number / chat session id / whatever
                        identifies this person on this channel
    raw_text:           what they said/typed this turn
    channel_metadata:   anything channel-specific worth keeping (call_id,
                        timestamp, language, session_id for multi-session
                        channels, etc.)

    Returns the text to speak (VAPI) or send back (WhatsApp/Email/SMS).
    """
    result, _ = await invoke_pipeline(channel, user_id, raw_text, channel_metadata)
    
    if "__interrupt__" in result:
        return "I have submitted your request for review. I will notify you as soon as it's approved."
        
    return result.get("final_response", "I'm sorry, something went wrong. Please try again.")
