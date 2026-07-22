"""
PipelineState -- state for the master Elarion graph (app/pipeline.py).

Deliberately structured as a superset of OrchestratorState (see
app/orchestrator/state.py): request, user_profile, intent, urgency, entities,
response, error are the exact same field names. That's what lets the compiled
orchestrator_graph be added directly as a node in the master graph via
workflow.add_node("orchestrator", orchestrator_graph) -- LangGraph maps the
shared keys onto the parent state automatically on entry and merges the
subgraph's output back onto them on exit. No wrapper needed for this one.

department_result / final_response are master-graph-only fields, written by
the department wrapper nodes in app/department_nodes.py.

Maintenance and FAQ are NOT folded into this schema -- MaintenanceState and
FAQState are deliberately isolated (see faq/state.py's own docstring) and
share no keys with this state or each other. They're invoked from thin
wrapper node functions instead of being added as direct subgraph nodes --
see app/department_nodes.py for that pattern.
"""
from typing import TypedDict, Dict, Any, Optional
from app.orchestrator.schemas import UnifiedRequest, UnifiedResponse


class PipelineState(TypedDict):
    # --- Shared with OrchestratorState (Layer 2) ---
    request: UnifiedRequest
    user_profile: Optional[Dict[str, Any]]
    intent: Optional[str]
    urgency: Optional[str]
    entities: Dict[str, Any]
    response: Optional[UnifiedResponse]
    error: Optional[str]

    # --- Master-graph-only fields ---
    active_department: Optional[str]              # which subgraph is active for this user (bypass orchestrator)
    department_result: Optional[Dict[str, Any]]  # raw final state from whichever Layer 3 subgraph ran
    final_response: Optional[str]                 # what actually gets spoken/sent back to the channel
