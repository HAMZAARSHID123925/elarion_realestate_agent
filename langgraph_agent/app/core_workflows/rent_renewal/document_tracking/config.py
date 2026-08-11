"""
Renewal Document Tracking Configuration — Phase 4, Workflow #4.

Defines standard required document types, labels, and file upload rules.
"""
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Standard required document definitions with human-readable descriptions
DOCUMENT_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "signed_lease_agreement": {
        "label": "Signed Renewal Lease Agreement",
        "description": "The signed copy of the updated 12-month or customized lease contract.",
        "mandatory": True,
    },
    "cnic_copy": {
        "label": "Government CNIC / National ID Copy",
        "description": "Front and back copy of the primary tenant's valid national identity card.",
        "mandatory": True,
    },
    "proof_of_income": {
        "label": "Updated Proof of Income / Employment",
        "description": "Latest salary slip, bank statement, or employment verification letter.",
        "mandatory": False,
    },
    "deposit_receipt": {
        "label": "Security Deposit Confirmation Receipt",
        "description": "Receipt or deposit confirmation slip if rent or deposit adjustment applies.",
        "mandatory": False,
    },
}

DEFAULT_MANDATORY_DOCUMENTS = ["signed_lease_agreement", "cnic_copy"]


def get_required_document_types() -> List[str]:
    """
    Returns list of required document type keys.
    Can be configured via RENEWAL_REQUIRED_DOCUMENTS environment variable.
    """
    custom = os.getenv("RENEWAL_REQUIRED_DOCUMENTS", "").strip()
    if custom:
        docs = [d.strip() for d in custom.split(",") if d.strip()]
        if docs:
            return docs
    return list(DEFAULT_MANDATORY_DOCUMENTS)


def get_document_label(doc_type: str) -> str:
    """Returns human-readable label for a document type key."""
    doc_info = DOCUMENT_DEFINITIONS.get(doc_type)
    if doc_info:
        return doc_info["label"]
    return doc_type.replace("_", " ").title()
