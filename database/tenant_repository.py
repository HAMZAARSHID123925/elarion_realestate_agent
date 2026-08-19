"""
Tenant Repository — Phase 2 Database Unification.

Canonical PostgreSQL data access for Tenant entities and Rent Reminder state.
Uses async psycopg with row_factory=dict_row.
Connects via DATABASE_URL.
"""
import os
import sys
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Ensure root directories are on path and load .env
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


class TenantRepository:
    """Canonical PostgreSQL repository for Tenant and Rent Reminder persistence."""

    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def _url(self) -> str:
        return self._db_url or get_db_url()

    async def get_tenant_by_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single tenant record by primary key (tenant_id).
        """
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT tenant_id, property_id, unit_id, tenant_name, name,
                           tenant_phone, phone_or_email, property_address,
                           rent_due_date, last_payment_date, rent_amount,
                           payment_status, reminder_30_sent_at, reminder_5_sent_at,
                           response_received, human_escalated, escalation_reason,
                           manual_hold, last_reminder_status, created_at, updated_at
                    FROM tenants
                    WHERE tenant_id = %s;
                    """,
                    (tenant_id,)
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def get_unpaid_overdue_tenants(self, ref_date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Queries all tenant records where payment_status != 'paid' and rent_due_date < ref_date.
        """
        if not ref_date_str:
            ref_date_str = date.today().isoformat()

        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT tenant_id, property_id, unit_id, tenant_name, name,
                           tenant_phone, phone_or_email, property_address,
                           rent_due_date, last_payment_date, rent_amount,
                           payment_status, reminder_30_sent_at, reminder_5_sent_at,
                           response_received, human_escalated, escalation_reason,
                           manual_hold, last_reminder_status, created_at, updated_at
                    FROM tenants
                    WHERE payment_status != 'paid'
                      AND rent_due_date < %s
                    ORDER BY rent_due_date ASC;
                    """,
                    (ref_date_str,)
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def list_tenants(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieves a paginated list of all tenants.
        """
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT tenant_id, property_id, unit_id, tenant_name, name,
                           tenant_phone, phone_or_email, property_address,
                           rent_due_date, last_payment_date, rent_amount,
                           payment_status, manual_hold, last_reminder_status, created_at
                    FROM tenants
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s;
                    """,
                    (limit, offset)
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def update_reminder_status(
        self,
        tenant_id: str,
        last_reminder_status: str,
        reminder_30_sent_at: Optional[str] = None,
        reminder_5_sent_at: Optional[str] = None,
        human_escalated: Optional[bool] = None,
        escalation_reason: Optional[str] = None,
        payment_status: Optional[str] = None,
        response_received: Optional[bool] = None,
    ) -> bool:
        """
        Idempotently updates reminder timestamps, status flags, and escalation fields.
        """
        db_url = self._url()
        updates = ["last_reminder_status = %s", "updated_at = CURRENT_TIMESTAMP"]
        params: List[Any] = [last_reminder_status]

        if reminder_30_sent_at is not None:
            updates.append("reminder_30_sent_at = %s")
            params.append(reminder_30_sent_at)
        if reminder_5_sent_at is not None:
            updates.append("reminder_5_sent_at = %s")
            params.append(reminder_5_sent_at)
        if human_escalated is not None:
            updates.append("human_escalated = %s")
            params.append(bool(human_escalated))
        if escalation_reason is not None:
            updates.append("escalation_reason = %s")
            params.append(escalation_reason)
        if payment_status is not None:
            updates.append("payment_status = %s")
            params.append(payment_status)
        if response_received is not None:
            updates.append("response_received = %s")
            params.append(bool(response_received))

        params.append(tenant_id)
        sql = f"UPDATE tenants SET {', '.join(updates)} WHERE tenant_id = %s;"

        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                await conn.commit()
                return cur.rowcount > 0

    async def update_payment_status(
        self,
        tenant_id: str,
        payment_status: str,
        last_payment_date: Optional[str] = None
    ) -> bool:
        """
        Updates the payment status and optional payment date for a tenant.
        """
        db_url = self._url()
        updates = ["payment_status = %s", "updated_at = CURRENT_TIMESTAMP"]
        params: List[Any] = [payment_status]

        if last_payment_date is not None:
            updates.append("last_payment_date = %s")
            params.append(last_payment_date)

        params.append(tenant_id)
        sql = f"UPDATE tenants SET {', '.join(updates)} WHERE tenant_id = %s;"

        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                await conn.commit()
                return cur.rowcount > 0

    async def set_manual_hold(self, tenant_id: str, manual_hold: bool) -> bool:
        """
        Sets or clears manual hold override flag for a tenant.
        """
        db_url = self._url()
        sql = "UPDATE tenants SET manual_hold = %s, updated_at = CURRENT_TIMESTAMP WHERE tenant_id = %s;"
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (manual_hold, tenant_id))
                await conn.commit()
                return cur.rowcount > 0

    async def check_connection(self) -> bool:
        """
        Pings PostgreSQL database to verify connectivity with fast timeout.
        """
        import asyncio
        db_url = self._url()
        try:
            conn = await asyncio.wait_for(
                psycopg.AsyncConnection.connect(db_url),
                timeout=1.0
            )
            async with conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("SELECT 1;")
                    row = await cur.fetchone()
                    return row is not None
        except Exception:
            return False

    async def create_tenant(self, data: Dict[str, Any]) -> str:
        """
        Creates a new tenant record.
        """
        db_url = self._url()
        tenant_id = data.get("tenant_id")
        # Ensure tenant_id exists
        if not tenant_id:
            import uuid
            tenant_id = f"T-{uuid.uuid4().hex[:8].upper()}"

        fields = [
            "tenant_id", "property_id", "unit_id", "tenant_name", "name",
            "tenant_phone", "phone_or_email", "property_address",
            "rent_amount", "rent_due_date", "payment_status"
        ]
        
        values_list = []
        for f in fields:
            if f == "tenant_id":
                values_list.append(tenant_id)
            else:
                values_list.append(data.get(f))
                
        placeholders = ", ".join(["%s"] * len(fields))
        columns = ", ".join(fields)
        
        sql = f"INSERT INTO tenants ({columns}) VALUES ({placeholders}) RETURNING tenant_id;"
        
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, values_list)
                result = await cur.fetchone()
                await conn.commit()
                return result[0] if result else tenant_id

    async def update_tenant(self, tenant_id: str, data: Dict[str, Any]) -> bool:
        """
        Updates an existing tenant record.
        """
        if not data:
            return True

        db_url = self._url()
        updates = []
        params = []
        
        allowed_fields = [
            "tenant_name", "name", "tenant_phone", "phone_or_email",
            "property_address", "rent_amount", "rent_due_date", "payment_status"
        ]
        
        for k, v in data.items():
            if k in allowed_fields and v is not None:
                updates.append(f"{k} = %s")
                params.append(v)
                
        if not updates:
            return True
            
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(tenant_id)
        
        sql = f"UPDATE tenants SET {', '.join(updates)} WHERE tenant_id = %s;"
        
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                await conn.commit()
                return cur.rowcount > 0


# Default shared singleton instance
tenant_repository = TenantRepository()
