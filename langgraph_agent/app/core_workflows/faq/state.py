"""
FAQState -- Workflow #3 (Tenant Support & FAQ Automation) state.

Own TypedDict, isolated from MaintenanceState. This is the FAQ department's
own clipboard, per the subgraph pattern: nothing here is shared with any
other department's state. The router's adapter functions are the only
bridge between this and the orchestrator's UnifiedResponse.
"""
from typing import TypedDict, Annotated, Optional, Dict, Any, List, Literal
from langgraph.graph.message import add_messages


class RetrievedChunk(TypedDict):
    text: str
    source: str              # source document filename / doc_id
    section: Optional[str]   # section/header, for citation (design doc section 4, "Citation Strategy")
    score: float              # similarity score from the vector search


class FAQState(TypedDict):
    # Conversation memory (same reducer pattern as MaintenanceState)
    messages: Annotated[list, add_messages]

    # Identity / continuity
    user_id: Optional[str]
    session_id: Optional[str]   # design doc section 5.1 / 7.4 - keys multi-turn slot accumulation

    # Turn input
    user_query: str

    # Classification output (structured output, design doc section 2.1 / 7.1)
    intent: Optional[Literal["KNOWLEDGE", "PROPERTY", "MIXED", "UNCLEAR"]]

    # --- Knowledge path (RAG) ---
    rag_context: List[RetrievedChunk]
    confidence_score: Optional[float]
    knowledge_answer: Optional[str]
    escalate: bool
    escalation_reason: Optional[str]

    # --- Property path (MCP) ---
    property_filters: Dict[str, Any]        # accumulated slots: location, property_type, budget, bedrooms
    missing_property_fields: List[str]
    mcp_results: Optional[Dict[str, Any]]
    recommendation_text: Optional[str]

    # --- Mixed / Unclear control ---
    clarify_question: Optional[str]

    # Final merged output, handed back to the router's adapter
    final_response: Optional[str]
