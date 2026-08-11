"""
Comprehensive Test Suite for Phase 5 — Human Escalation & Manager Intervention (Workflow #4).

Tests:
  - Escalation Detection Engine: Reason mapping, priority classification, and trigger detection.
  - Manager Decision Processing: Action validation, status transitions, and workflow resumption.
  - Repository & Audit Trail: Idempotent escalation creation and audit logging.
  - Modular LangGraph Nodes: escalation_detection_node, human_escalation_node, manager_action_node.
  - End-to-End Subgraph Execution: Full lifecycle covering escalation, manager decision injection,
    and workflow resumption into Phase 4 document checking.
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
# 1. Escalation Detection Engine Unit Tests
# ============================================================================

from app.core_workflows.rent_renewal.human_escalation.detector import (
    detect_escalation_requirement,
)


class TestEscalationDetectionEngine:
    """Tests for pure escalation detection and classification logic."""

    def test_tenant_explicit_human_request(self):
        """When tenant asks to speak with a human or manager, flags TENANT_REQUESTED_HUMAN."""
        state = {
            "tenant_response": "Please have the property manager call me directly to discuss.",
        }
        is_req, reason, priority, desc = detect_escalation_requirement(state)
        assert is_req is True
        assert reason == "TENANT_REQUESTED_HUMAN"
        assert priority == "MEDIUM"

    def test_tenant_negotiation_detection(self):
        """When renewal_intent is NEGOTIATION, flags NEGOTIATION_REQUIRED with HIGH priority."""
        state = {
            "renewal_intent": "NEGOTIATION",
            "tenant_response": "I want to stay, but please reduce rent by 10%.",
        }
        is_req, reason, priority, desc = detect_escalation_requirement(state)
        assert is_req is True
        assert reason == "NEGOTIATION_REQUIRED"
        assert priority == "HIGH"

    def test_renewal_approval_required_for_yes_intent(self):
        """When tenant confirms renewal intent (YES), flags RENEWAL_APPROVAL_REQUIRED (HITL rule)."""
        state = {
            "renewal_intent": "YES",
            "tenant_response": "Yes, I would love to renew my lease for another 12 months.",
        }
        is_req, reason, priority, desc = detect_escalation_requirement(state)
        assert is_req is True
        assert reason == "RENEWAL_APPROVAL_REQUIRED"
        assert priority == "MEDIUM"

    def test_document_issue_detection(self):
        """When document_status is REJECTED or document_exception is True, flags DOCUMENT_ISSUE."""
        state = {
            "document_status": "REJECTED",
        }
        is_req, reason, priority, desc = detect_escalation_requirement(state)
        assert is_req is True
        assert reason == "DOCUMENT_ISSUE"

    def test_workflow_error_detection(self):
        """When operational workflow_error exists, flags WORKFLOW_ERROR with HIGH priority."""
        state = {
            "workflow_error": "Database connection timeout during lease query.",
        }
        is_req, reason, priority, desc = detect_escalation_requirement(state)
        assert is_req is True
        assert reason == "WORKFLOW_ERROR"
        assert priority == "HIGH"

    def test_no_escalation_for_routine_states(self):
        """Standard reminder checks, declines, or unclear responses do not trigger unprompted escalations."""
        state_decline = {"renewal_intent": "NO", "tenant_response": "No, moving out."}
        is_req, reason, _, _ = detect_escalation_requirement(state_decline)
        assert is_req is False

        state_unclear = {"renewal_intent": "UNCLEAR", "tenant_response": "Where is the parking?"}
        is_req, reason, _, _ = detect_escalation_requirement(state_unclear)
        assert is_req is False


# ============================================================================
# 2. Manager Decision Processing Unit Tests
# ============================================================================

from app.core_workflows.rent_renewal.human_escalation.service import (
    process_manager_decision,
)


class TestManagerDecisionProcessing:
    """Tests for manager decision validation and resumption mapping."""

    @pytest.mark.asyncio
    async def test_approve_continuation_resumes_to_document_phase(self):
        """APPROVE_CONTINUATION sets next status to RENEWAL_IN_PROGRESS (resuming Phase 4)."""
        with patch(
            "app.core_workflows.rent_renewal.human_escalation.service.repository.record_manager_decision",
            new_callable=AsyncMock,
        ) as mock_rec:
            res = await process_manager_decision(
                escalation_id=10,
                action="APPROVE_CONTINUATION",
                notes="Tenant has excellent payment history. Approved.",
            )

            assert res["next_renewal_status"] == "RENEWAL_IN_PROGRESS"
            assert res["escalation_status"] == "RESOLVED"
            mock_rec.assert_called_once_with(
                escalation_id=10,
                manager_action="APPROVE_CONTINUATION",
                manager_notes="Tenant has excellent payment history. Approved.",
                new_status="RESOLVED",
                actor="Property Manager",
            )

    @pytest.mark.asyncio
    async def test_reject_continuation_closes_workflow(self):
        """REJECT_CONTINUATION sets next status to TENANT_DECLINED and closes escalation."""
        with patch(
            "app.core_workflows.rent_renewal.human_escalation.service.repository.record_manager_decision",
            new_callable=AsyncMock,
        ):
            res = await process_manager_decision(
                escalation_id=11,
                action="REJECT_CONTINUATION",
                notes="Property scheduled for major renovation.",
            )

            assert res["next_renewal_status"] == "TENANT_DECLINED"
            assert res["escalation_status"] == "CLOSED"

    @pytest.mark.asyncio
    async def test_request_more_information_prompts_clarification(self):
        """REQUEST_MORE_INFORMATION transitions to CLARIFICATION_REQUIRED."""
        with patch(
            "app.core_workflows.rent_renewal.human_escalation.service.repository.record_manager_decision",
            new_callable=AsyncMock,
        ):
            res = await process_manager_decision(
                escalation_id=12,
                action="REQUEST_MORE_INFORMATION",
                notes="Ask tenant if they are willing to sign for 24 months.",
            )

            assert res["next_renewal_status"] == "CLARIFICATION_REQUIRED"
            assert res["escalation_status"] == "PENDING_MANAGER_ACTION"

    @pytest.mark.asyncio
    async def test_invalid_manager_action_raises_error(self):
        """Invalid manager decision string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid manager action"):
            await process_manager_decision(escalation_id=13, action="INVALID_DECISION")


# ============================================================================
# 3. Repository & Idempotency Tests
# ============================================================================

from app.core_workflows.rent_renewal.human_escalation.service import (
    trigger_human_escalation,
)


class TestEscalationServiceAndIdempotency:
    """Tests for escalation creation, idempotency, and audit logging."""

    @pytest.mark.asyncio
    async def test_trigger_human_escalation_creates_record(self):
        state = {
            "lease_id": "L-001",
            "tenant_id": "T-100",
            "property_id": "P-100",
            "tenant_name": "Hamza Arshid",
            "renewal_intent": "NEGOTIATION",
            "tenant_response": "Lower rent please",
        }

        with patch(
            "app.core_workflows.rent_renewal.human_escalation.service.repository.create_escalation",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = 301
            res = await trigger_human_escalation(state)

            assert res["escalation_required"] is True
            assert res["escalation_id"] == 301
            assert res["escalation_reason"] == "NEGOTIATION_REQUIRED"
            assert res["escalation_priority"] == "HIGH"


# ============================================================================
# 4. Modular LangGraph Nodes Tests
# ============================================================================

from app.core_workflows.rent_renewal.nodes.escalation_detection_node import escalation_detection_node
from app.core_workflows.rent_renewal.nodes.human_escalation_node import human_escalation_node
from app.core_workflows.rent_renewal.nodes.manager_action_node import manager_action_node


class TestHumanEscalationNodes:
    """Tests for Phase 5 LangGraph modular nodes."""

    def test_escalation_detection_node(self):
        state = {
            "tenant_response": "Please have the manager call me",
            "logs": [],
        }
        res = escalation_detection_node(state)
        assert res["escalation_required"] is True
        assert res["escalation_reason"] == "TENANT_REQUESTED_HUMAN"

    @pytest.mark.asyncio
    async def test_human_escalation_node(self):
        state = {
            "lease_id": "L-001",
            "tenant_id": "T-100",
            "renewal_intent": "NEGOTIATION",
            "logs": [],
        }
        with patch(
            "app.core_workflows.rent_renewal.nodes.human_escalation_node.trigger_human_escalation",
            new_callable=AsyncMock,
        ) as mock_trig:
            mock_trig.return_value = {
                "escalation_id": 401,
                "escalation_reason": "NEGOTIATION_REQUIRED",
            }
            res = await human_escalation_node(state)

            assert res["escalation_id"] == 401
            assert res["escalation_status"] == "PENDING_MANAGER_ACTION"
            assert res["renewal_status"] == "ESCALATED"
            assert res["notification_status"] == "manager_alerted"

    @pytest.mark.asyncio
    async def test_manager_action_node_approval(self):
        state = {
            "escalation_id": 401,
            "manager_action": "APPROVE_CONTINUATION",
            "manager_notes": "Terms approved",
            "logs": [],
        }
        with patch(
            "app.core_workflows.rent_renewal.nodes.manager_action_node.process_manager_decision",
            new_callable=AsyncMock,
        ) as mock_proc:
            mock_proc.return_value = {
                "next_renewal_status": "RENEWAL_IN_PROGRESS",
                "escalation_status": "RESOLVED",
            }
            res = await manager_action_node(state)

            assert res["renewal_status"] == "RENEWAL_IN_PROGRESS"
            assert res["escalation_status"] == "RESOLVED"


# ============================================================================
# 5. End-to-End Subgraph Execution with Human-in-the-Loop & Resumption
# ============================================================================

from app.core_workflows.rent_renewal.graph import rent_renewal_graph


class TestRentRenewalSubgraphHumanEscalationEndToEnd:
    """Tests the full LangGraph subgraph covering escalation and workflow resumption."""

    @pytest.mark.asyncio
    async def test_subgraph_routes_to_escalation_on_negotiation(self):
        """When tenant requests negotiation -> creates escalation and pauses at PENDING_MANAGER_ACTION."""
        state = {
            "lease_id": "L-001",
            "tenant_id": "T-100",
            "tenant_name": "Hamza Arshid",
            "property_address": "123 Main St Apt 4B",
            "action": "ESCALATE",
            "escalation_reason": "NEGOTIATION_REQUIRED",
            "renewal_intent": "NEGOTIATION",
            "tenant_response": "I want to renew but need a discount on rent.",
            "monthly_rent": 75000.0,
            "logs": [],
        }

        with patch(
            "app.core_workflows.rent_renewal.nodes.human_escalation_node.trigger_human_escalation",
            new_callable=AsyncMock,
        ) as mock_esc:
            mock_esc.return_value = {
                "escalation_id": 501,
                "escalation_reason": "NEGOTIATION_REQUIRED",
            }
            result = await rent_renewal_graph.ainvoke(state)

        assert result["renewal_intent"] == "NEGOTIATION"
        assert result["escalation_id"] == 501
        assert result["renewal_status"] == "ESCALATED"
        assert result["escalation_status"] == "PENDING_MANAGER_ACTION"
        assert result["is_complete"] is True

    @pytest.mark.asyncio
    async def test_subgraph_resumes_to_document_tracking_after_manager_approval(self):
        """When manager provides APPROVE_CONTINUATION -> resumes workflow into Phase 4 document checklist."""
        state = {
            "lease_id": "L-001",
            "tenant_id": "T-100",
            "tenant_name": "Hamza Arshid",
            "property_address": "123 Main St Apt 4B",
            "action": "APPLY_MANAGER_ACTION",
            "escalation_id": 501,
            "manager_action": "APPROVE_CONTINUATION",
            "manager_notes": "Special 5% discount authorized. Proceed to contract signing.",
            "required_documents": ["signed_lease_agreement", "cnic_copy"],
            "received_documents": [],
            "logs": [],
        }

        with patch(
            "app.core_workflows.rent_renewal.nodes.manager_action_node.process_manager_decision",
            new_callable=AsyncMock,
        ) as mock_proc:
            mock_proc.return_value = {
                "next_renewal_status": "RENEWAL_IN_PROGRESS",
                "escalation_status": "RESOLVED",
            }
            result = await rent_renewal_graph.ainvoke(state)

        # Verified that manager approval seamlessly transitioned into Phase 4 document checklist
        assert result["escalation_status"] == "RESOLVED"
        assert result["renewal_status"] == "DOCUMENTS_PENDING"
        assert "signed_lease_agreement" in result["missing_documents"]
        assert "Signed Renewal Lease Agreement" in result["document_request_message"]
        assert result["is_complete"] is True


if __name__ == "__main__":
    pytest.main(["-v", __file__])
