"""
Maintenance Repository — Phase 4 API Layer & Phase 5 SLA Escalation.

Canonical PostgreSQL data access for Maintenance Tickets, Vendors, and Ticket Logs.
Uses async psycopg with row_factory=dict_row.
Connects via DATABASE_URL.
"""
import os
import uuid
import logging
from typing import List, Dict, Any, Optional

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Ensure root directories are loaded
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for env_path in [os.path.join(root_dir, ".env"), os.path.join(root_dir, "langgraph_agent", ".env")]:
    if os.path.exists(env_path):
        load_dotenv(env_path)

load_dotenv()

logger = logging.getLogger(__name__)


def get_db_url() -> str:
    """Returns DATABASE_URL, raising if not configured."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url


class MaintenanceRepository:
    """Canonical PostgreSQL repository for Maintenance Tickets and Vendors."""

    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def _url(self) -> str:
        return self._db_url or get_db_url()

    async def list_tickets(
        self,
        status: Optional[str] = None,
        urgency: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieves maintenance tickets matching optional filter criteria.
        """
        conditions = []
        params: List[Any] = []

        if status:
            conditions.append("UPPER(status) = UPPER(%s)")
            params.append(status)
        if urgency:
            conditions.append("LOWER(urgency) = LOWER(%s)")
            params.append(urgency)
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT ticket_id, tenant_id, property_id, unit_id, category,
                   description, urgency, permission_to_enter, pets_present,
                   status, source_channel, created_by, idempotency_key,
                   vendor_id, assignment_status, last_escalated_at, escalation_level,
                   created_at
            FROM maintenance_tickets
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s;
        """
        params.append(limit)

        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql, params)
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single maintenance ticket record by ID.
        """
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT ticket_id, tenant_id, property_id, unit_id, category,
                           description, urgency, permission_to_enter, pets_present,
                           status, source_channel, created_by, idempotency_key,
                           vendor_id, assignment_status, last_escalated_at, escalation_level,
                           created_at
                    FROM maintenance_tickets
                    WHERE ticket_id = %s;
                    """,
                    (ticket_id,)
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def create_ticket(
        self,
        tenant_id: str,
        property_id: Optional[str],
        unit_id: Optional[str],
        category: str,
        description: str,
        urgency: str = "low",
        permission_to_enter: str = "unconfirmed",
        pets_present: str = "unconfirmed",
        source_channel: str = "api",
        created_by: Optional[str] = "api_user",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new maintenance ticket and logs the initial status entry.
        """
        db_url = self._url()
        ticket_id = f"TICK-{uuid.uuid4().hex[:8].upper()}"
        idem_key = idempotency_key or f"idem-{uuid.uuid4()}"

        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                # Insert ticket
                await cur.execute(
                    """
                    INSERT INTO maintenance_tickets (
                        ticket_id, tenant_id, property_id, unit_id, category,
                        description, urgency, permission_to_enter, pets_present,
                        status, source_channel, created_by, idempotency_key,
                        assignment_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (
                        ticket_id, tenant_id, property_id, unit_id, category,
                        description, urgency, permission_to_enter, pets_present,
                        "OPEN", source_channel, created_by, idem_key,
                        "UNASSIGNED"
                    )
                )
                row = await cur.fetchone()

                # Insert status log
                await cur.execute(
                    """
                    INSERT INTO ticket_status_log (ticket_id, old_status, new_status)
                    VALUES (%s, %s, %s);
                    """,
                    (ticket_id, None, "OPEN")
                )
                await conn.commit()
                return dict(row)

    async def record_ticket_escalation(
        self,
        ticket_id: str,
        escalation_level: str
    ) -> bool:
        """
        Dudably marks ticket as escalated with timestamp to prevent duplicate hourly alerts.
        """
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    UPDATE maintenance_tickets
                    SET last_escalated_at = CURRENT_TIMESTAMP,
                        escalation_level = %s
                    WHERE ticket_id = %s;
                    """,
                    (escalation_level, ticket_id)
                )
                # Log to status transition history
                await cur.execute(
                    """
                    INSERT INTO ticket_status_log (ticket_id, old_status, new_status)
                    VALUES (%s, %s, %s);
                    """,
                    (ticket_id, "OPEN", f"ESCALATED_{escalation_level}")
                )
                await conn.commit()
                return cur.rowcount > 0

    async def get_ticket_status_log(self, ticket_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the status transition history for a ticket.
        """
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT log_id, ticket_id, old_status, new_status, timestamp
                    FROM ticket_status_log
                    WHERE ticket_id = %s
                    ORDER BY timestamp ASC;
                    """,
                    (ticket_id,)
                )
                rows = await cur.fetchall()
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> bool:
        """
        Updates specific fields on a maintenance ticket (e.g. status, assigned_vendor_id).
        """
        if not updates:
            return True
            
        db_url = self._url()
        set_clauses = []
        params = []
        
        allowed_fields = [
            "status", "urgency", "assigned_vendor_id", 
            "permission_to_enter", "pets_present"
        ]
        
        for k, v in updates.items():
            if k in allowed_fields:
                set_clauses.append(f"{k} = %s")
                params.append(v)
                
        if not set_clauses:
            return True
            
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        params.append(ticket_id)
        
        sql = f"UPDATE maintenance_tickets SET {', '.join(set_clauses)} WHERE ticket_id = %s RETURNING status;"
        
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                # get old status first if we're updating status
                old_status = None
                if "status" in updates:
                    await cur.execute("SELECT status FROM maintenance_tickets WHERE ticket_id = %s;", (ticket_id,))
                    row = await cur.fetchone()
                    if row:
                        old_status = row[0]
                
                await cur.execute(sql, params)
                new_status = updates.get("status")
                
                if old_status and new_status and old_status != new_status:
                    await cur.execute(
                        """
                        INSERT INTO ticket_status_log (ticket_id, old_status, new_status)
                        VALUES (%s, %s, %s);
                        """,
                        (ticket_id, old_status, new_status)
                    )
                    
                await conn.commit()
                return cur.rowcount > 0


# Shared singleton instance
maintenance_repository = MaintenanceRepository()
