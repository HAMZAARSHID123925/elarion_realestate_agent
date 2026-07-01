from typing import TypedDict, Dict, Any, Optional
from app.orchestrator.schemas import UnifiedRequest, UnifiedResponse

class OrchestratorState(TypedDict):
    """
    The state maintained throughout the Layer 2 Orchestrator graph execution.
    """
    request: UnifiedRequest
    user_profile: Optional[Dict[str, Any]]  # Filled by Identification Node
    intent: Optional[str]                   # Filled by Classification Node
    urgency: Optional[str]                  # Filled by Urgency Node
    entities: Dict[str, Any]                # Filled by Extraction Node
    response: Optional[UnifiedResponse]     # The final output
    error: Optional[str]
