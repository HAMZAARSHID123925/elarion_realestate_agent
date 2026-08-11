"""
Comprehensive Test Suite for Phase 4 — Renewal Document Tracking (Workflow #4).

Tests:
  - Checklist Evaluation Engine: Complete, Under Review, Partially Submitted, and Pending states.
  - Document Request Formatter: Human-readable missing document prompts.
  - Repository & Service: Document persistence, status transitions, and notification generation.
  - Modular LangGraph Nodes: document_check_node, document_request_node, document_verification_node.
  - End-to-End Subgraph Execution: Routing through document tracking paths.
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
# 1. Checklist Evaluation Engine Unit Tests
# ============================================================================

from app.core_workflows.rent_renewal.document_tracking.checker import (
    evaluate_document_checklist,
    format_missing_documents_request,
)
from app.core_workflows.rent_renewal.document_tracking.config import (
    get_required_document_types,
    get_document_label,
)


class TestDocumentChecklistEngine:
    """Tests for pure document evaluation logic."""

    REQUIRED_DOCS = ["signed_lease_agreement", "cnic_copy"]

    def test_zero_documents_pending_status(self):
        """When no documents have been submitted, status is PENDING and all are missing."""
        submitted = []
        result = evaluate_document_checklist(self.REQUIRED_DOCS, submitted)

        assert result["document_status"] == "PENDING"
        assert result["completion_percentage"] == 0.0
        assert set(result["missing_docs"]) == set(self.REQUIRED_DOCS)
        assert result["received_docs"] == []

    def test_partial_submission(self):
        """When 1 of 2 documents is submitted, status is PARTIALLY_SUBMITTED."""
        submitted = [
            {"doc_type": "signed_lease_agreement", "status": "SUBMITTED"}
        ]
        result = evaluate_document_checklist(self.REQUIRED_DOCS, submitted)

        assert result["document_status"] == "PARTIALLY_SUBMITTED"
        assert result["completion_percentage"] == 50.0
        assert result["received_docs"] == ["signed_lease_agreement"]
        assert result["missing_docs"] == ["cnic_copy"]

    def test_all_submitted_under_review(self):
        """When all required documents are submitted (not yet verified), status is UNDER_REVIEW."""
        submitted = [
            {"doc_type": "signed_lease_agreement", "status": "SUBMITTED"},
            {"doc_type": "cnic_copy", "status": "SUBMITTED"},
        ]
        result = evaluate_document_checklist(self.REQUIRED_DOCS, submitted)

        assert result["document_status"] == "UNDER_REVIEW"
        assert result["completion_percentage"] == 100.0
        assert result["missing_docs"] == []
        assert len(result["received_docs"]) == 2

    def test_all_verified_complete(self):
        """When all required documents are VERIFIED, status is COMPLETE."""
        submitted = [
            {"doc_type": "signed_lease_agreement", "status": "VERIFIED"},
            {"doc_type": "cnic_copy", "status": "VERIFIED"},
        ]
        result = evaluate_document_checklist(self.REQUIRED_DOCS, submitted)

        assert result["document_status"] == "COMPLETE"
        assert result["completion_percentage"] == 100.0
        assert result["missing_docs"] == []
        assert len(result["verified_docs"]) == 2

    def test_rejected_document_excluded_from_received(self):
        """A REJECTED document is not counted as received and remains in missing_docs."""
        submitted = [
            {"doc_type": "signed_lease_agreement", "status": "SUBMITTED"},
            {"doc_type": "cnic_copy", "status": "REJECTED"},
        ]
        result = evaluate_document_checklist(self.REQUIRED_DOCS, submitted)

        assert result["document_status"] == "PARTIALLY_SUBMITTED"
        assert result["completion_percentage"] == 50.0
        assert result["missing_docs"] == ["cnic_copy"]

    def test_format_missing_documents_request(self):
        """Renders clear, polite request with human-readable document labels."""
        missing = ["signed_lease_agreement", "cnic_copy"]
        msg = format_missing_documents_request(
            tenant_name="Hamza Arshid",
            property_address="Apt 4B, Gulberg Heights",
            missing_docs=missing,
            lease_end_date="2026-11-10",
        )
        assert "Hamza Arshid" in msg
        assert "Apt 4B, Gulberg Heights" in msg
        assert "Signed Renewal Lease Agreement" in msg
        assert "Government CNIC / National ID Copy" in msg
        assert "2026-11-10" in msg


# ============================================================================
# 2. Document Service & Repository Tests
# ============================================================================

from app.core_workflows.rent_renewal.document_tracking.service import (
    get_document_status_summary,
    submit_renewal_document,
    generate_missing_documents_notification,
)


class TestDocumentTrackingService:
    """Tests for document upload processing and notification service."""

    @pytest.mark.asyncio
    async def test_get_document_status_summary(self):
        with patch(
            "app.core_workflows.rent_renewal.document_tracking.service.repository.get_lease_documents",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = [
                {"doc_type": "signed_lease_agreement", "status": "SUBMITTED"}
            ]

            summary = await get_document_status_summary(
                lease_id="L-001",
                required_docs=["signed_lease_agreement", "cnic_copy"],
            )

            assert summary["document_status"] == "PARTIALLY_SUBMITTED"
            assert summary["missing_docs"] == ["cnic_copy"]

    @pytest.mark.asyncio
    async def test_submit_renewal_document(self):
        with patch(
            "app.core_workflows.rent_renewal.document_tracking.service.repository.record_document_upload",
            new_callable=AsyncMock,
        ) as mock_rec, patch(
            "app.core_workflows.rent_renewal.document_tracking.service.repository.get_lease_documents",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_rec.return_value = 201
            mock_get.return_value = [
                {"doc_type": "signed_lease_agreement", "status": "SUBMITTED"},
                {"doc_type": "cnic_copy", "status": "SUBMITTED"},
            ]

            result = await submit_renewal_document(
                lease_id="L-001",
                tenant_id="T-100",
                doc_type="cnic_copy",
                file_name="cnic_front_back.pdf",
                required_docs=["signed_lease_agreement", "cnic_copy"],
            )

            assert result["document_id"] == 201
            assert result["document_status"] == "UNDER_REVIEW"
            assert result["completion_percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_generate_missing_documents_notification(self):
        with patch(
            "app.core_workflows.rent_renewal.document_tracking.service.repository.get_lease_documents",
            new_callable=AsyncMock,
        ) as mock_get:
            # 1. Missing docs -> returns formatted notification
            mock_get.return_value = []
            notif = await generate_missing_documents_notification(
                lease_id="L-001",
                tenant_name="Hamza",
                property_address="Apt 4B",
                required_docs=["signed_lease_agreement"],
            )
            assert notif is not None
            assert "Signed Renewal Lease Agreement" in notif["request_message"]

            # 2. Complete docs -> returns None
            mock_get.return_value = [
                {"doc_type": "signed_lease_agreement", "status": "VERIFIED"}
            ]
            notif_complete = await generate_missing_documents_notification(
                lease_id="L-001",
                tenant_name="Hamza",
                property_address="Apt 4B",
                required_docs=["signed_lease_agreement"],
            )
            assert notif_complete is None


# ============================================================================
# 3. Individual Document Tracking Nodes Tests
# ============================================================================

from app.core_workflows.rent_renewal.nodes.document_check_node import document_check_node
from app.core_workflows.rent_renewal.nodes.document_request_node import document_request_node
from app.core_workflows.rent_renewal.nodes.document_verification_node import document_verification_node


class TestDocumentTrackingNodes:
    """Tests for Phase 4 LangGraph modular nodes."""

    def test_document_check_node_missing(self):
        state = {
            "lease_id": "L-001",
            "required_documents": ["signed_lease_agreement", "cnic_copy"],
            "received_documents": [{"doc_type": "signed_lease_agreement", "status": "SUBMITTED"}],
            "logs": [],
        }
        res = document_check_node(state)
        assert res["document_status"] == "PARTIALLY_SUBMITTED"
        assert res["missing_documents"] == ["cnic_copy"]
        assert res["renewal_status"] == "DOCUMENTS_PENDING"

    def test_document_check_node_complete(self):
        state = {
            "lease_id": "L-001",
            "required_documents": ["signed_lease_agreement"],
            "received_documents": [{"doc_type": "signed_lease_agreement", "status": "VERIFIED"}],
            "logs": [],
        }
        res = document_check_node(state)
        assert res["document_status"] == "COMPLETE"
        assert res["missing_documents"] == []
        assert res["renewal_status"] == "DOCUMENTS_COMPLETE"

    def test_document_request_node(self):
        state = {
            "tenant_name": "Hamza",
            "property_address": "Apt 4B",
            "missing_documents": ["cnic_copy"],
            "logs": [],
        }
        res = document_request_node(state)
        assert "Government CNIC" in res["document_request_message"]
        assert res["final_response"] == res["document_request_message"]

    def test_document_verification_node(self):
        state = {
            "document_status": "UNDER_REVIEW",
            "received_documents": [{"doc_type": "signed_lease_agreement", "status": "SUBMITTED"}],
            "logs": [],
        }
        res = document_verification_node(state)
        assert res["document_status"] == "COMPLETE"
        assert res["renewal_status"] == "DOCUMENTS_COMPLETE"
        assert res["received_documents"][0]["status"] == "VERIFIED"


# ============================================================================
# 4. End-to-End Subgraph Execution for Document Tracking
# ============================================================================

from app.core_workflows.rent_renewal.graph import rent_renewal_graph


class TestRentRenewalSubgraphDocumentTracking:
    """Tests the full LangGraph subgraph routing through document tracking paths."""

    @pytest.mark.asyncio
    async def test_subgraph_routes_to_document_request_when_missing(self):
        """When renewal is in document stage with missing items -> generates document request."""
        state = {
            "lease_id": "L-001",
            "tenant_id": "T-100",
            "tenant_name": "Hamza Arshid",
            "property_address": "123 Main St Apt 4B",
            "renewal_status": "RENEWAL_IN_PROGRESS",
            "required_documents": ["signed_lease_agreement", "cnic_copy"],
            "received_documents": [],
            "logs": [],
        }

        result = await rent_renewal_graph.ainvoke(state)

        assert result["renewal_status"] == "DOCUMENTS_PENDING"
        assert result["document_status"] == "PENDING"
        assert set(result["missing_documents"]) == {"signed_lease_agreement", "cnic_copy"}
        assert "Signed Renewal Lease Agreement" in result["document_request_message"]
        assert result["is_complete"] is True

    @pytest.mark.asyncio
    async def test_subgraph_routes_to_verification_when_complete(self):
        """When renewal has all documents submitted -> verifies and completes."""
        state = {
            "lease_id": "L-001",
            "tenant_id": "T-100",
            "tenant_name": "Hamza Arshid",
            "property_address": "123 Main St Apt 4B",
            "action": "CHECK_DOCUMENTS",
            "required_documents": ["signed_lease_agreement", "cnic_copy"],
            "received_documents": [
                {"doc_type": "signed_lease_agreement", "status": "SUBMITTED"},
                {"doc_type": "cnic_copy", "status": "SUBMITTED"},
            ],
            "logs": [],
        }

        result = await rent_renewal_graph.ainvoke(state)

        assert result["document_status"] == "COMPLETE"
        assert result["renewal_status"] == "DOCUMENTS_COMPLETE"
        assert result["missing_documents"] == []
        assert result["is_complete"] is True


if __name__ == "__main__":
    pytest.main(["-v", __file__])
