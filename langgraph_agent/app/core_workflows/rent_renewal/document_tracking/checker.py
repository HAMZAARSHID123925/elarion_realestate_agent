"""
Renewal Document Checklist Evaluation Engine — Phase 4, Workflow #4.

Pure deterministic functions to evaluate document checklists, calculate
missing items, determine document status, and format missing document requests.
No DB, no LLM, no side effects. Fully unit-testable.
"""
from typing import List, Dict, Any, Tuple
from app.core_workflows.rent_renewal.document_tracking.config import get_document_label


def evaluate_document_checklist(
    required_docs: List[str],
    submitted_docs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluates submitted documents against the required checklist.

    Args:
        required_docs: List of required document type strings (e.g. ['signed_lease_agreement', 'cnic_copy']).
        submitted_docs: List of document dicts with 'doc_type' and 'status'.

    Returns:
        Dict containing:
            received_docs (List[str]): Types of documents successfully received (status != 'REJECTED').
            verified_docs (List[str]): Types of documents marked VERIFIED.
            missing_docs (List[str]): Types of required documents not yet submitted.
            completion_percentage (float): Percentage (0.0 to 100.0) of required docs submitted.
            document_status (str): COMPLETE | UNDER_REVIEW | PARTIALLY_SUBMITTED | PENDING
    """
    if not required_docs:
        return {
            "received_docs": [],
            "verified_docs": [],
            "missing_docs": [],
            "completion_percentage": 100.0,
            "document_status": "COMPLETE",
        }

    # Extract received and verified document types (ignoring REJECTED)
    received_types = set()
    verified_types = set()

    for doc in submitted_docs:
        dtype = doc.get("doc_type")
        dstatus = (doc.get("status") or "SUBMITTED").upper()

        if dtype and dstatus != "REJECTED":
            received_types.add(dtype)
            if dstatus == "VERIFIED":
                verified_types.add(dtype)

    received_list = [d for d in required_docs if d in received_types]
    verified_list = [d for d in required_docs if d in verified_types]
    missing_list = [d for d in required_docs if d not in received_types]

    total_required = len(required_docs)
    total_received = len(received_list)
    total_verified = len(verified_list)

    completion_pct = round((total_received / total_required) * 100.0, 1)

    # Determine overall document status
    if total_verified == total_required:
        doc_status = "COMPLETE"
    elif total_received == total_required:
        doc_status = "UNDER_REVIEW"
    elif total_received > 0:
        doc_status = "PARTIALLY_SUBMITTED"
    else:
        doc_status = "PENDING"

    return {
        "received_docs": received_list,
        "verified_docs": verified_list,
        "missing_docs": missing_list,
        "completion_percentage": completion_pct,
        "document_status": doc_status,
    }


def format_missing_documents_request(
    tenant_name: str,
    property_address: str,
    missing_docs: List[str],
    lease_end_date: str = "",
) -> str:
    """
    Renders a clear, polite natural language request for missing renewal documents.
    """
    bullet_points = []
    for doc_type in missing_docs:
        label = get_document_label(doc_type)
        bullet_points.append(f"  • {label}")

    docs_list_text = "\n".join(bullet_points)

    message = (
        f"Dear {tenant_name},\n\n"
        f"Regarding the renewal of your lease agreement for {property_address}"
        f"{f' (expiring on {lease_end_date})' if lease_end_date else ''}:\n\n"
        f"To complete your renewal paperwork and formalize the tenancy agreement, "
        f"we kindly request that you submit the following required document(s):\n\n"
        f"{docs_list_text}\n\n"
        f"Please reply to this message attaching the document(s) or upload them through your tenant portal.\n\n"
        f"Thank you for your prompt cooperation.\n\n"
        f"Sincerely,\n"
        f"Elarion Property Management Team"
    )
    return message
