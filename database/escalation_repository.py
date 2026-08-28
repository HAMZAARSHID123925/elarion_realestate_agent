"""
Escalation Repository — Phase 7 API Layer.

Canonical PostgreSQL data access for Human Escalations.
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

class EscalationRepository:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def _url(self) -> str:
        return self._db_url or get_db_url()

    async def list_escalations(
        self,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        lease_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        db_url = self._url()
        conditions = []
        params = []
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        if assigned_to:
            conditions.append("assigned_to = %s")
            params.append(assigned_to)
        if lease_id:
            conditions.append("lease_id = %s")
            params.append(lease_id)
            
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        sql = f"""
            SELECT escalation_id, lease_id, tenant_id, property_id,
                   escalation_reason, escalation_priority, status,
                   description, assigned_to, notified_at, manager_action,
                   manager_notes, resolved_at, created_at, updated_at
            FROM human_escalations
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

    async def update_escalation(
        self,
        escalation_id: int,
        updates: Dict[str, Any],
        actor: str = "system"
    ) -> bool:
        """
        Updates an escalation and optionally logs the action.
        """
        if not updates:
            return True

        db_url = self._url()
        set_clauses = []
        params = []
        
        allowed_fields = [
            "status", "assigned_to", "manager_action", "manager_notes", "resolved_at"
        ]
        
        for k, v in updates.items():
            if k in allowed_fields:
                set_clauses.append(f"{k} = %s")
                params.append(v)
                
        if not set_clauses:
            return True
            
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        params.append(escalation_id)
        
        sql = f"UPDATE human_escalations SET {', '.join(set_clauses)} WHERE escalation_id = %s RETURNING status, lease_id, tenant_id;"
        
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                row = await cur.fetchone()
                
                if row:
                    # Insert audit log if status changed or manager action occurred
                    event_type = "MANAGER_ACTION_RECEIVED" if "manager_action" in updates else "ESCALATION_UPDATED"
                    if updates.get("status") in ["RESOLVED", "CLOSED", "REJECTED"]:
                        event_type = "ESCALATION_RESOLVED"
                        
                    await cur.execute(
                        """
                        INSERT INTO escalation_audit_logs 
                        (escalation_id, lease_id, tenant_id, event_type, actor, details)
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (escalation_id, row[1], row[2], event_type, actor, psycopg.types.json.Jsonb(updates))
                    )
                
                await conn.commit()
                return cur.rowcount > 0

escalation_repository = EscalationRepository()
