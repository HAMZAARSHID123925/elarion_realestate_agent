"""
Test Suite for Rent Renewal Subgraph Workflow Nodes.
Tests intent classification, decline handling, and clarification prompt generation.
"""
import pytest
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure root directories are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core_workflows.rent_renewal.nodes.intent_classification_node import intent_classification_node
from app.core_workflows.rent_renewal.nodes.decline_node import decline_node
from app.core_workflows.rent_renewal.nodes.clarification_node import clarification_node
from app.core_workflows.rent_renewal.renewal_intent.classifier import RenewalIntentResult


@pytest.mark.asyncio
async def test_intent_classification_node_positive():
    """Tests intent classification for positive renewal intent."""
    state = {
        "tenant_response": "Yes, I would love to renew my lease for another 12 months.",
        "lease_id": "L-100",
        "tenant_id": "T-100",
        "logs": []
    }

    mock_result = RenewalIntentResult(
        intent="YES",
        confidence=0.95,
        reasoning="Explicit confirmation to renew",
        requested_term_months=12,
        proposed_rent=None
    )

    with patch("app.core_workflows.rent_renewal.nodes.intent_classification_node.classify_renewal_intent", new=AsyncMock(return_value=mock_result)), \
         patch("app.core_workflows.rent_renewal.nodes.intent_classification_node.record_renewal_intent", new=AsyncMock()):

        res = await intent_classification_node(state)
        assert res["renewal_intent"] == "YES"
        assert res["renewal_status"] == "PENDING_MANAGER_REVIEW"
        assert res["intent_confidence"] == 0.95


def test_decline_node_execution():
    """Tests decline node when tenant decides to vacate."""
    state = {
        "tenant_id": "T-301",
        "property_address": "Apartment 4B, Gulberg",
        "lease_end_date": "2026-09-30",
        "renewal_intent": "NO",
        "logs": []
    }
    res = decline_node(state)
    assert res["renewal_status"] == "TENANT_DECLINED"
    assert res["tenant_decision"] == "declined"
    assert "move-out" in res["final_response"].lower()


def test_clarification_node_execution():
    """Tests clarification node when tenant response is ambiguous."""
    state = {
        "tenant_id": "T-302",
        "tenant_name": "Hamza",
        "property_address": "House 12, DHA",
        "lease_end_date": "2026-10-31",
        "renewal_intent": "UNCLEAR",
        "logs": []
    }
    res = clarification_node(state)
    assert res["renewal_status"] == "CLARIFICATION_REQUIRED"
    assert "clarify" in res["final_response"].lower()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
