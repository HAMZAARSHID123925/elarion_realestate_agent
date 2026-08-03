"""
Rent Renewal Workflow LangGraph Subgraph.
"""
from langgraph.graph import StateGraph, START, END
from app.core_workflows.rent_renewal.state import RentRenewalState
from app.core_workflows.rent_renewal.nodes import lease_check_node, renewal_offer_node

def build_rent_renewal_graph():
    builder = StateGraph(RentRenewalState)
    builder.add_node("lease_check", lease_check_node)
    builder.add_node("renewal_offer", renewal_offer_node)
    
    builder.add_edge(START, "lease_check")
    builder.add_edge("lease_check", "renewal_offer")
    builder.add_edge("renewal_offer", END)
    
    return builder.compile()

rent_renewal_graph = build_rent_renewal_graph()
