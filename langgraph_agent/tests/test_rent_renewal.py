"""
Test Suite for Rent Renewal Workflow.
Tests lease details check, standard 5% renewal calculation, and tenant decision handling.
"""
import pytest
import os
import sys

# Ensure root directories are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core_workflows.rent_renewal.graph import rent_renewal_graph
from app.core_workflows.rent_renewal.nodes import lease_check_node, renewal_offer_node

def test_rent_renewal_accepted_flow():
    """Tests rent renewal workflow when tenant accepts the 5% renewal offer."""
    initial_state = {
        "tenant_id": "T-201",
        "current_rent": 80000.0,
        "renewal_term_months": 12,
        "messages": [{"role": "user", "content": "Yes, I agree and accept the renewal offer."}],
        "is_complete": False
    }

    final_state = rent_renewal_graph.invoke(initial_state)

    assert final_state["current_rent"] == 80000.0
    assert final_state["offered_rent"] == 84000.0  # 80000 * 1.05
    assert final_state["tenant_decision"] == "accepted"
    assert final_state["is_complete"] is True
    assert "addendum" in final_state["final_response"].lower()

def test_rent_renewal_rejected_flow():
    """Tests rent renewal workflow when tenant rejects/declines the offer."""
    initial_state = {
        "tenant_id": "T-202",
        "current_rent": 100000.0,
        "renewal_term_months": 12,
        "messages": [{"role": "user", "content": "No, I am moving out."}],
        "is_complete": False
    }

    final_state = rent_renewal_graph.invoke(initial_state)

    assert final_state["offered_rent"] == 105000.0
    assert final_state["tenant_decision"] == "rejected"
    assert final_state["is_complete"] is True
    assert "move-out" in final_state["final_response"].lower()

def test_rent_renewal_negotiating_flow():
    """Tests rent renewal workflow when tenant requests discount/negotiation."""
    initial_state = {
        "tenant_id": "T-203",
        "current_rent": 60000.0,
        "renewal_term_months": 12,
        "messages": [{"role": "user", "content": "Can you offer a lower discount rate?"}],
        "is_complete": False
    }

    final_state = rent_renewal_graph.invoke(initial_state)

    assert final_state["tenant_decision"] == "negotiating"
    assert final_state["is_complete"] is True
    assert "negotiation request" in final_state["final_response"].lower()

if __name__ == "__main__":
    pytest.main(["-v", __file__])
