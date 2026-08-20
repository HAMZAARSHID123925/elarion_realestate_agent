"""
Document Repository — Phase 7 API Layer.

Canonical PostgreSQL data access for Renewal Documents.
"""
import os
import logging
from typing import List, Dict, Any, Optional

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url

class DocumentRepository:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def _url(self) -> str:
        return self._db_url or get_db_url()

    async def list_documents(
        self,
        lease_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        db_url = self._url()
        conditions = []
        params = []
        
        if lease_id:
            conditions.append("lease_id = %s")
            params.append(lease_id)
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if status:
            conditions.append("status = %s")
            params.append(status)
            
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        sql = f"""
            SELECT document_id, lease_id, tenant_id, doc_type, file_name,
                   file_url, status, uploaded_at, verified_at, verified_by,
                   rejection_reason, created_at
            FROM renewal_documents
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s;
        """
        params.extend([limit, offset])
        
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql, params)
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

document_repository = DocumentRepository()
