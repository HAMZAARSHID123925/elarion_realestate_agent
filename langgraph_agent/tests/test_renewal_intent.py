"""
Comprehensive Test Suite for Phase 3 — Renewal Intent & Manager Notification (Workflow #4).

Tests:
  - Intent Classifier: Affirmative (YES), Negative (NO), Negotiation (NEGOTIATION), Unclear (UNCLEAR).
  - Manager Notification Service: Structured review task generation and HITL boundary enforcement.
  - Modular LangGraph Nodes: Individual tests for all Phase 3 nodes.
  - End-to-End Graph Execution: Multi-path routing for all 4 intent outcomes and proactive reminders.
"""
import pytest
import os
import sys
from datetime import date, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

# Ensure root directories are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


# ============================================================================
# 1. Intent Classifier Unit Tests (Rule Fallback & Logic)
# ============================================================================

from app.core_workflows.rent_renewal.renewal_intent.classifier import (
    _rule_based_fallback_classify,
    classify_renewal_intent,
    RenewalIntentResult,
)


class TestIntentClassifier:
    """Tests for renewal intent classification logic."""

    def test_affirmative_intent_phrases(self):
        """Phrases confirming renewal classify as YES."""
        phrases = [
            "Yes, I would like to renew my lease for another year.",
            "We definitely want to stay living here, please send the renewal contract.",
            "Happy to renew!",
            "I want to extend my tenancy for another 12 months.",
            "Sure, count me in to continue.",
        ]
        for phrase in phrases:
            res = _rule_based_fallback_classify(phrase)
            assert res.intent == "YES", f"Failed on phrase: '{phrase}'"
            assert res.confidence >= 0.90

    def test_negative_intent_phrases(self):
        """Phrases declining renewal classify as NO."""
        phrases = [
            "No, I will not be renewing. Moving out at the end of the term.",
            "We found another apartment and are relocating next month.",
            "I cannot stay and will vacate the property.",
            "We won't renew our lease.",
        ]
        for phrase in phrases:
            res = _rule_based_fallback_classify(phrase)
            assert res.intent == "NO", f"Failed on phrase: '{phrase}'"
            assert res.confidence >= 0.90

    def test_negotiation_intent_phrases(self):
        """Phrases requesting discounts, lower rent, or custom terms classify as NEGOTIATION."""
        phrases = [
            "I want to renew, but can you do a discount on the monthly rent?",
            "The rent is too high. If you lower rent to 70000, I will stay.",
            "Can we negotiate the price for a 2-year lease?",
            "What if we reduce the rent slightly?",
        ]
        for phrase in phrases:
            res = _rule_based_fallback_classify(phrase)
            assert res.intent == "NEGOTIATION", f"Failed on phrase: '{phrase}'"
            assert res.confidence >= 0.85

    def test_unclear_intent_phrases(self):
        """Ambiguous or unrelated queries classify as UNCLEAR."""
        phrases = [
            "Where is the nearest grocery store?",
            "Thanks for the message.",
            "What is the weather today?",
            "",
            "   ",
        ]
        for phrase in phrases:
            res = _rule_based_fallback_classify(phrase)
            assert res.intent == "UNCLEAR", f"Failed on phrase: '{phrase}'"

    @pytest.mark.asyncio
    async def test_classify_renewal_intent_fallback(self):
        """classify_renewal_intent falls back gracefully when GROQ_API_KEY is not set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GROQ_API_KEY", None)
            res = await classify_renewal_intent("I want to renew my lease for 12 months.")
            assert isinstance(res, RenewalIntentResult)
            assert res.intent == "YES"


# ============================================================================
# 2. Manager Notification Service Tests
# ============================================================================

from app.core_workflows.rent_renewal.renewal_intent.notifications import notify_manager_of_renewal_intent


class TestManagerNotificationService:
    """Tests for manager notification and Human-in-the-Loop review task creation."""

    @pytest.mark.asyncio
    async def test_notify_manager_yes_intent(self):
        """Creates formal review task when tenant intends to renew (enforces HITL boundary)."""
        with patch(
            "app.core_workflows.rent_renewal.renewal_intent.notifications.repository.create_manager_notification",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = 501

            result = await notify_manager_of_renewal_intent(
                lease_id="L-001",
                tenant_id="T-100",
                tenant_name="Hamza Arshid",
                property_id="P-100",
                property_address="Apt 4B, Gulberg Heights",
                intent="YES",
                tenant_response="Yes, I want to renew for 1 year.",
                current_rent=75000.0,
                lease_end_date="2026-11-10",
            )

            assert result["notification_id"] == 501
            assert result["notification_type"] == "RENEWAL_INTENT_YES"
            assert result["status"] == "MANAGER_ALERTED"
            assert result["details"]["human_decision_pending"] is True
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_manager_negotiation_intent(self):
        """Creates negotiation task when tenant requests term or rent changes."""
        with patch(
            "app.core_workflows.rent_renewal.renewal_intent.notifications.repository.create_manager_notification",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = 502

            result = await notify_manager_of_renewal_intent(
                lease_id="L-002",
                tenant_id="T-101",
                tenant_name="John Doe",
                property_id="P-100",
                property_address="Unit 12",
                intent="NEGOTIATION",
                tenant_response="Can we reduce rent to 85,000?",
                current_rent=95000.0,
                lease_end_date="2026-10-10",
                proposed_rent=85000.0,
            )

            assert result["notification_id"] == 502
            assert result["notification_type"] == "RENEWAL_NEGOTIATION"
            assert result["details"]["proposed_rent"] == 85000.0


# ============================================================================
# 3. Individual Node Unit Tests
# ============================================================================

from app.core_workflows.rent_renewal.nodes.intent_classification_node import intent_classification_node
from app.core_workflows.rent_renewal.nodes.manager_notification_node import manager_notification_node
from app.core_workflows.rent_renewal.nodes.decline_node import decline_node
from app.core_workflows.rent_renewal.nodes.clarification_node import clarification_node
from app.core_workflows.rent_renewal.nodes.tracker_node import renewal_tracker_node


class TestIndividualNodes:
    """Tests for each modular node function."""

    @pytest.mark.asyncio
    async def test_intent_classification_node_yes(self):
        state = {
            "lease_id": "L-001",
            "tenant_id": "T-100",
            "tenant_response": "I want to continue living here.",
            "logs": [],
        }
        with patch(
            "app.core_workflows.rent_renewal.nodes.intent_classification_node.record_renewal_intent",
            new_callable=AsyncMock,
        ):
            res = await intent_classification_node(state)
        assert res["renewal_intent"] == "YES"
        assert res["renewal_status"] == "PENDING_MANAGER_REVIEW"

    @pytest.mark.asyncio
    async def test_manager_notification_node(self):
        state = {
            "lease_id": "L-001",
            "tenant_id": "T-100",
            "tenant_name": "Hamza Arshid",
            "renewal_intent": "YES",
            "tenant_response": "I want to renew.",
            "logs": [],
        }
        with patch(
            "app.core_workflows.rent_renewal.nodes.manager_notification_node.notify_manager_of_renewal_intent",
            new_callable=AsyncMock,
        ) as mock_notif:
            mock_notif.return_value = {"notification_id": 99}
            res = await manager_notification_node(state)

        assert res["renewal_status"] == "PENDING_MANAGER_REVIEW"
        assert res["manager_notification_id"] == 99
        assert res["notification_status"] == "manager_alerted"

    def test_decline_node(self):
        state = {
            "tenant_id": "T-101",
            "property_address": "Villa 12",
            "lease_end_date": "2026-09-30",
            "logs": [],
        }
        res = decline_node(state)
        assert res["renewal_status"] == "TENANT_DECLINED"
        assert res["tenant_decision"] == "declined"
        assert "move-out" in res["final_response"]

    def test_clarification_node(self):
        state = {
            "tenant_name": "Ali",
            "property_address": "Apt 4B",
            "lease_end_date": "2026-10-31",
            "logs": [],
        }
        res = clarification_node(state)
        assert res["renewal_status"] == "CLARIFICATION_REQUIRED"
        assert "clarify whether you would like to renew" in res["clarification_question"]

    def test_tracker_node(self):
        # Complete when status is PENDING_MANAGER_REVIEW or TENANT_DECLINED
        state_complete = {"renewal_status": "PENDING_MANAGER_REVIEW", "logs": []}
        assert renewal_tracker_node(state_complete)["is_complete"] is True

        # Incomplete when awaiting clarification
        state_incomplete = {"renewal_status": "CLARIFICATION_REQUIRED", "logs": []}
        assert renewal_tracker_node(state_incomplete)["is_complete"] is False


# ============================================================================
# 4. End-to-End Subgraph Routing Tests
# ============================================================================

from app.core_workflows.rent_renewal.graph import rent_renewal_graph


class TestRentRenewalSubgraphEndToEnd:
    """Tests the full LangGraph subgraph for all intent outcomes and proactive reminders."""

    @pytest.mark.asyncio
    async def test_full_graph_yes_intent(self):
        """Tenant says YES -> classified as YES -> alerts manager -> status is PENDING_MANAGER_REVIEW."""
        state = {
            "lease_id": "L-001",
            "tenant_id": "T-100",
            "tenant_name": "Hamza Arshid",
            "property_address": "123 Main St Apt 4B",
            "tenant_response": "Yes, I would like to renew my lease for another year.",
            "monthly_rent": 75000.0,
            "logs": [],
        }

        with patch(
            "app.core_workflows.rent_renewal.nodes.intent_classification_node.record_renewal_intent",
            new_callable=AsyncMock,
        ), patch(
            "app.core_workflows.rent_renewal.nodes.manager_notification_node.notify_manager_of_renewal_intent",
            new_callable=AsyncMock,
        ) as mock_notif:
            mock_notif.return_value = {"notification_id": 1001}
            result = await rent_renewal_graph.ainvoke(state)

        assert result["renewal_intent"] == "YES"
        assert result["renewal_status"] == "PENDING_MANAGER_REVIEW"
        assert result["manager_notification_id"] == 1001
        assert result["is_complete"] is True

    @pytest.mark.asyncio
    async def test_full_graph_no_intent(self):
        """Tenant says NO -> classified as NO -> routes to decline -> status is TENANT_DECLINED."""
        state = {
            "lease_id": "L-002",
            "tenant_id": "T-101",
            "tenant_name": "John Doe",
            "property_address": "123 Main St Unit 12",
            "tenant_response": "No, I am moving out at the end of the term.",
            "logs": [],
        }

        with patch(
            "app.core_workflows.rent_renewal.nodes.intent_classification_node.record_renewal_intent",
            new_callable=AsyncMock,
        ):
            result = await rent_renewal_graph.ainvoke(state)

        assert result["renewal_intent"] == "NO"
        assert result["renewal_status"] == "TENANT_DECLINED"
        assert result["tenant_decision"] == "declined"
        assert result["is_complete"] is True

    @pytest.mark.asyncio
    async def test_full_graph_negotiation_intent(self):
        """Tenant wants discount -> classified as NEGOTIATION -> alerts manager."""
        state = {
            "lease_id": "L-003",
            "tenant_id": "T-102",
            "tenant_name": "Sara Khan",
            "property_address": "Villa 12, DHA Phase 5",
            "tenant_response": "I want to stay, but the price is too high. Can we negotiate a discount?",
            "monthly_rent": 120000.0,
            "logs": [],
        }

        with patch(
            "app.core_workflows.rent_renewal.nodes.intent_classification_node.record_renewal_intent",
            new_callable=AsyncMock,
        ), patch(
            "app.core_workflows.rent_renewal.nodes.manager_notification_node.notify_manager_of_renewal_intent",
            new_callable=AsyncMock,
        ) as mock_notif:
            mock_notif.return_value = {"notification_id": 1002}
            result = await rent_renewal_graph.ainvoke(state)

        assert result["renewal_intent"] == "NEGOTIATION"
        assert result["renewal_status"] == "PENDING_MANAGER_REVIEW"
        assert result["manager_notification_id"] == 1002
        assert result["is_complete"] is True

    @pytest.mark.asyncio
    async def test_full_graph_unclear_intent(self):
        """Tenant asks unrelated question -> classified as UNCLEAR -> generates clarification."""
        state = {
            "lease_id": "L-004",
            "tenant_id": "T-103",
            "tenant_name": "Ali",
            "property_address": "Studio 15",
            "tenant_response": "Where can I park my bicycle?",
            "logs": [],
        }

        with patch(
            "app.core_workflows.rent_renewal.nodes.intent_classification_node.record_renewal_intent",
            new_callable=AsyncMock,
        ):
            result = await rent_renewal_graph.ainvoke(state)

        assert result["renewal_intent"] == "UNCLEAR"
        assert result["renewal_status"] == "CLARIFICATION_REQUIRED"
        assert "clarify whether you would like to renew" in result["clarification_question"]
        assert result["is_complete"] is False

    @pytest.mark.asyncio
    async def test_full_graph_proactive_reminder_regression(self):
        """Proactive reminder check without tenant response still functions correctly."""
        today = date.today()
        state = {
            "tenant_id": "T-100",
            "tenant_name": "Hamza Arshid",
            "tenant_contact": "hamza@example.com",
            "property_address": "123 Main St Apt 4B",
            "lease_end_date": (today + timedelta(days=60)).isoformat(),
            "monthly_rent": 75000.0,
            "reminder_count": 0,
            "logs": [],
        }

        with patch(
            "app.core_workflows.rent_renewal.nodes.reminder_send_node.dispatch_reminder",
            new_callable=AsyncMock,
        ) as mock_disp:
            mock_disp.return_value = {"success": True, "status": "SENT"}
            result = await rent_renewal_graph.ainvoke(state)

        assert result["renewal_status"] == "REMINDER_SENT"
        assert result["reminder_count"] == 1
        assert result["last_reminder_type"] == "LEASE_EXPIRY_60_DAYS"
        assert result["is_complete"] is True


if __name__ == "__main__":
    pytest.main(["-v", __file__])
