"""
Lease Repository — Phase 7 API Layer.

Canonical PostgreSQL data access for Lease entities.
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

class LeaseRepository:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def _url(self) -> str:
        return self._db_url or get_db_url()

    async def get_lease_by_id(self, lease_id: str) -> Optional[Dict[str, Any]]:
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT lease_id, tenant_id, property_id, unit_id, 
                           lease_start_date, lease_end_date, monthly_rent, status, created_at
                    FROM leases
                    WHERE lease_id = %s;
                    """,
                    (lease_id,)
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def list_leases(
        self,
        tenant_id: Optional[str] = None,
        property_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        db_url = self._url()
        conditions = []
        params = []
        
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if property_id:
            conditions.append("property_id = %s")
            params.append(property_id)
        if status:
            conditions.append("status = %s")
            params.append(status)
            
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        sql = f"""
            SELECT lease_id, tenant_id, property_id, unit_id, 
                   lease_start_date, lease_end_date, monthly_rent, status, created_at
            FROM leases
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

    async def list_expiry_events(
        self,
        lease_id: Optional[str] = None,
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
        if status:
            conditions.append("event_status = %s")
            params.append(status)
            
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        sql = f"""
            SELECT id, event_name, lease_id, tenant_id, property_id,
                   expiry_date, days_remaining, window_days, event_date,
                   event_status, created_at
            FROM lease_expiry_events
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

lease_repository = LeaseRepository()
