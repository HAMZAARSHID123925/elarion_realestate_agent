"""
Document Check Node — Phase 4, Workflow #4.

Evaluates the renewal document checklist for a lease, identifies missing items,
and computes overall document completion status.
"""
import logging
from typing import Dict, Any, List

from app.core_workflows.rent_renewal.state import RentRenewalState
from app.core_workflows.rent_renewal.document_tracking.config import get_required_document_types
from app.core_workflows.rent_renewal.document_tracking.checker import evaluate_document_checklist

logger = logging.getLogger(__name__)


def document_check_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: document_check_node
    Evaluates required_documents against received_documents in state.
    """
    logs = state.get("logs", [])
    tenant_id = state.get("tenant_id", "T-UNKNOWN")
    lease_id = state.get("lease_id", "L-UNKNOWN")

    required_docs = state.get("required_documents") or get_required_document_types()
    received_docs_raw = state.get("received_documents") or []

    # Format into checklist evaluation input
    submitted_list = []
    for doc in received_docs_raw:
        if isinstance(doc, dict):
            submitted_list.append(doc)
        elif isinstance(doc, str):
            submitted_list.append({"doc_type": doc, "status": "SUBMITTED"})

    eval_result = evaluate_document_checklist(required_docs, submitted_list)
    doc_status = eval_result["document_status"]
    missing_docs = eval_result["missing_docs"]
    completion_pct = eval_result["completion_percentage"]

    # Map to renewal_status
    if doc_status == "COMPLETE":
        new_renewal_status = "DOCUMENTS_COMPLETE"
    elif doc_status == "UNDER_REVIEW":
        new_renewal_status = "DOCUMENTS_UNDER_REVIEW"
    else:
        new_renewal_status = "DOCUMENTS_PENDING"

    logs.append(
        f"[document_check_node] Evaluated docs for lease {lease_id}: "
        f"status={doc_status} ({completion_pct}%), missing={missing_docs}"
    )

    return {
        "required_documents": required_docs,
        "received_documents": received_docs_raw,
        "missing_documents": missing_docs,
        "document_status": doc_status,
        "renewal_status": new_renewal_status,
        "logs": logs,
    }
