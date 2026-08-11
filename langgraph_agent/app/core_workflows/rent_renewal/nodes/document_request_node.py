"""
Document Request Node — Phase 4, Workflow #4.

Triggered when required renewal documents are missing.
Renders a clear missing-document request and prepares it for tenant communication.
"""
import logging
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState
from app.core_workflows.rent_renewal.document_tracking.checker import format_missing_documents_request

logger = logging.getLogger(__name__)


def document_request_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: document_request_node
    Formats missing document request message.
    """
    logs = state.get("logs", [])
    tenant_name = state.get("tenant_name", "Resident")
    property_address = state.get("property_address", "the residence")
    lease_end_date = str(state.get("lease_end_date", ""))
    missing_docs = state.get("missing_documents") or []

    if missing_docs:
        request_message = format_missing_documents_request(
            tenant_name=tenant_name,
            property_address=property_address,
            missing_docs=missing_docs,
            lease_end_date=lease_end_date,
        )
    else:
        request_message = "All required renewal documents have been received. Thank you!"

    logs.append(
        f"[document_request_node] Generated document request message for missing docs: {missing_docs}"
    )

    return {
        "document_request_message": request_message,
        "final_response": request_message,
        "logs": logs,
    }
