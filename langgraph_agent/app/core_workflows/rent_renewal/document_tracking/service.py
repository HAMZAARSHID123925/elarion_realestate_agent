"""
Renewal Document Tracking Service — Phase 4, Workflow #4.

Coordinates document checklist evaluations, upload processing, and missing document requests.
"""
import logging
from typing import Dict, Any, List, Optional

from app.core_workflows.rent_renewal.document_tracking.config import get_required_document_types
from app.core_workflows.rent_renewal.document_tracking.checker import (
    evaluate_document_checklist,
    format_missing_documents_request,
)
from app.core_workflows.rent_renewal.document_tracking import repository

logger = logging.getLogger(__name__)


async def get_document_status_summary(
    lease_id: str,
    required_docs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Queries submitted documents from PostgreSQL and evaluates checklist status.

    Returns:
        Dict containing received_docs, verified_docs, missing_docs,
        completion_percentage, and document_status.
    """
    req_docs = required_docs or get_required_document_types()

    try:
        submitted = await repository.get_lease_documents(lease_id)
    except Exception as e:
        logger.error("Failed to query documents for lease %s: %s", lease_id, e)
        submitted = []

    return evaluate_document_checklist(req_docs, submitted)


async def submit_renewal_document(
    lease_id: str,
    tenant_id: str,
    doc_type: str,
    file_name: str,
    file_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    required_docs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Records a document upload and re-evaluates the lease document checklist.

    Returns:
        Dict with document_id and updated checklist summary.
    """
    doc_id = await repository.record_document_upload(
        lease_id=lease_id,
        tenant_id=tenant_id,
        doc_type=doc_type,
        file_name=file_name,
        file_url=file_url,
        status="SUBMITTED",
        metadata=metadata,
    )

    checklist_summary = await get_document_status_summary(lease_id, required_docs)

    return {
        "document_id": doc_id,
        "lease_id": lease_id,
        "doc_type": doc_type,
        "file_name": file_name,
        **checklist_summary,
    }


async def generate_missing_documents_notification(
    lease_id: str,
    tenant_name: str,
    property_address: str,
    lease_end_date: str = "",
    required_docs: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Evaluates missing documents and formats a request notification if any items are missing.

    Returns None if all required documents are already complete.
    """
    summary = await get_document_status_summary(lease_id, required_docs)
    missing_docs = summary.get("missing_docs", [])

    if not missing_docs:
        return None

    request_msg = format_missing_documents_request(
        tenant_name=tenant_name,
        property_address=property_address,
        missing_docs=missing_docs,
        lease_end_date=lease_end_date,
    )

    return {
        "missing_docs": missing_docs,
        "document_status": summary.get("document_status"),
        "completion_percentage": summary.get("completion_percentage"),
        "request_message": request_msg,
    }
