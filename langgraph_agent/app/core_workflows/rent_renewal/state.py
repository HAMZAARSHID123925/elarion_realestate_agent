"""
Rent Renewal Workflow State Schema.
"""
from typing import TypedDict, Optional, List, Dict, Any

class RentRenewalState(TypedDict, total=False):
    tenant_id: Optional[str]
    lease_id: Optional[str]
    unit_id: Optional[str]
    current_rent: Optional[float]
    offered_rent: Optional[float]
    renewal_term_months: Optional[int]
    tenant_decision: Optional[str]  # "accepted", "rejected", "negotiating"
    messages: List[Dict[str, Any]]
    final_response: Optional[str]
    is_complete: bool
