"""
Renewal Document Tracking Repository — Phase 4, Workflow #4.

Database access for storing submitted renewal documents, updating verification states,
and querying document history.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


def _get_db_url() -> str:
    url = DATABASE_URL or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url


async def record_document_upload(
    lease_id: str,
    tenant_id: str,
    doc_type: str,
    file_name: str,
    file_url: Optional[str] = None,
    status: str = "SUBMITTED",
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Inserts a newly uploaded document record into renewal_documents.
    Returns the document_id.
    """
    db_url = _get_db_url()
    meta_json = json.dumps(metadata or {})

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                INSERT INTO renewal_documents (
                    lease_id, tenant_id, doc_type, file_name,
                    file_url, status, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s::jsonb
                ) RETURNING document_id;
            """, (
                lease_id,
                tenant_id,
                doc_type,
                file_name,
                file_url or "",
                status,
                meta_json,
            ))
            row = await cur.fetchone()
            doc_id = row[0]
        await conn.commit()
    logger.info("Recorded document upload #%d: lease=%s type=%s file=%s", doc_id, lease_id, doc_type, file_name)
    return doc_id


async def get_lease_documents(lease_id: str) -> List[Dict[str, Any]]:
    """Retrieves all submitted documents for a specific lease."""
    db_url = _get_db_url()
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""
                SELECT document_id, lease_id, tenant_id, doc_type,
                       file_name, file_url, status, uploaded_at,
                       verified_at, verified_by, rejection_reason, metadata
                FROM renewal_documents
                WHERE lease_id = %s
                ORDER BY uploaded_at ASC;
            """, (lease_id,))
            rows = await cur.fetchall()
    return rows


async def update_document_status(
    document_id: int,
    status: str,
    verified_by: Optional[str] = None,
    rejection_reason: Optional[str] = None,
) -> None:
    """Updates the verification status of a submitted document."""
    db_url = _get_db_url()
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            if status == "VERIFIED":
                await cur.execute("""
                    UPDATE renewal_documents
                    SET status = %s,
                        verified_at = CURRENT_TIMESTAMP,
                        verified_by = %s
                    WHERE document_id = %s;
                """, (status, verified_by or "Property Manager", document_id))
            elif status == "REJECTED":
                await cur.execute("""
                    UPDATE renewal_documents
                    SET status = %s,
                        rejection_reason = %s
                    WHERE document_id = %s;
                """, (status, rejection_reason or "Document invalid or illegible", document_id))
            else:
                await cur.execute("""
                    UPDATE renewal_documents
                    SET status = %s
                    WHERE document_id = %s;
                """, (status, document_id))
        await conn.commit()
    logger.info("Updated document #%d status -> %s", document_id, status)
