from typing import TypedDict, Annotated, Optional, Dict, Any, List
from langgraph.graph.message import add_messages

class MaintenanceState(TypedDict):
    # Conversation memory
    messages: Annotated[list, add_messages]
    
    # Input user info
    user_id: Optional[str]
    
    # Mandatory slots
    tenant_identity: Optional[str]
    property_unit: Optional[str]
    issue_category: Optional[str]
    issue_description: Optional[str]
    urgency: Optional[str]
    permission_to_enter: Optional[str]
    pets_present: Optional[str]
    
    # Real DB IDs resolved by receptionist (separate from display names)
    db_tenant_id: Optional[str]
    db_unit_id: Optional[str]
    
    # State tracking
    missing_slots: List[str]
    ticket_payload: Optional[Dict[str, Any]]
    escalation_record: Optional[Dict[str, Any]]
    ticket_creation_status: Optional[str]
    ticket_creation_error: Optional[str]
    final_response: Optional[str]
