"""
Document Verification Node — Phase 4, Workflow #4.

Handles document verification state updates (e.g. following property manager review of submitted files).
"""
import logging
from typing import Dict, Any, List

from app.core_workflows.rent_renewal.state import RentRenewalState

logger = logging.getLogger(__name__)


def document_verification_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: document_verification_node
    Finalizes document verification status.
    """
    logs = state.get("logs", [])
    doc_status = state.get("document_status", "PENDING")
    received_docs = state.get("received_documents") or []

    # Update verification status in state
    verified_docs = []
    for doc in received_docs:
        if isinstance(doc, dict):
            doc_copy = dict(doc)
            if doc_copy.get("status") != "REJECTED":
                doc_copy["status"] = "VERIFIED"
            verified_docs.append(doc_copy)
        elif isinstance(doc, str):
            verified_docs.append({"doc_type": doc, "status": "VERIFIED"})

    logs.append(f"[document_verification_node] Verified {len(verified_docs)} submitted documents.")

    return {
        "received_documents": verified_docs,
        "document_status": "COMPLETE" if doc_status != "PENDING" else "PENDING",
        "renewal_status": "DOCUMENTS_COMPLETE",
        "logs": logs,
    }
