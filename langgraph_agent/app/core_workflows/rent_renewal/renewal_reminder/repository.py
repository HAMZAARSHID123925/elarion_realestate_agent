"""
Renewal Reminder Repository — Phase 2, Workflow #4.

Database access for Phase 2: querying pending expiry events, joining tenant
and lease details, inserting renewal_reminders records, and updating event status.
"""
import os
import json
import logging
from datetime import datetime
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


async def get_pending_expiry_events() -> List[Dict[str, Any]]:
    """
    Queries all lease_expiry_events where event_status = 'PENDING'.
    Joins tenant and property information for full reminder context.
    """
    db_url = _get_db_url()
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""
                SELECT 
                    e.id AS event_id,
                    e.event_name,
                    e.lease_id,
                    e.tenant_id,
                    e.property_id,
                    e.expiry_date,
                    e.days_remaining,
                    e.window_days,
                    e.event_date,
                    e.event_status,
                    e.run_id,
                    t.name AS tenant_name,
                    t.phone_or_email AS tenant_contact,
                    p.address AS property_address,
                    l.monthly_rent,
                    l.status AS lease_status
                FROM lease_expiry_events e
                JOIN leases l ON e.lease_id = l.lease_id
                JOIN tenants t ON e.tenant_id = t.tenant_id
                JOIN properties p ON e.property_id = p.property_id
                WHERE e.event_status = 'PENDING'
                ORDER BY e.created_at ASC;
            """)
            rows = await cur.fetchall()
    return rows


async def get_lease_reminder_context(lease_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves full lease, tenant, and property details for a specific lease ID.
    Used by conversational LangGraph nodes when processing a single lease.
    """
    db_url = _get_db_url()
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""
                SELECT 
                    l.lease_id,
                    l.tenant_id,
                    l.property_id,
                    l.unit_id,
                    l.lease_start_date,
                    l.lease_end_date,
                    l.monthly_rent,
                    l.status AS lease_status,
                    t.name AS tenant_name,
                    t.phone_or_email AS tenant_contact,
                    p.address AS property_address
                FROM leases l
                JOIN tenants t ON l.tenant_id = t.tenant_id
                JOIN properties p ON l.property_id = p.property_id
                WHERE l.lease_id = %s;
            """, (lease_id,))
            row = await cur.fetchone()
    return row


async def record_renewal_reminder(
    lease_id: str,
    tenant_id: str,
    property_id: str,
    channel: str,
    recipient: str,
    reminder_type: str,
    message_body: str,
    status: str = "SENT",
    event_id: Optional[int] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Inserts a record into renewal_reminders table.
    Returns the newly created reminder_id.
    """
    db_url = _get_db_url()
    meta_json = json.dumps(metadata or {})

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                INSERT INTO renewal_reminders (
                    event_id, lease_id, tenant_id, property_id,
                    channel, recipient, reminder_type, message_body,
                    status, error_message, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
                ) RETURNING reminder_id;
            """, (
                event_id,
                lease_id,
                tenant_id,
                property_id,
                channel,
                recipient,
                reminder_type,
                message_body,
                status,
                error_message,
                meta_json,
            ))
            row = await cur.fetchone()
            reminder_id = row[0]
        await conn.commit()
    return reminder_id


async def mark_expiry_event_status(event_id: int, new_status: str) -> None:
    """Updates event_status (e.g. to 'SENT' or 'FAILED') on lease_expiry_events."""
    db_url = _get_db_url()
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                UPDATE lease_expiry_events
                SET event_status = %s
                WHERE id = %s;
            """, (new_status, event_id))
        await conn.commit()


async def get_reminder_history(lease_id: str) -> List[Dict[str, Any]]:
    """Retrieves all sent renewal reminders for a given lease."""
    db_url = _get_db_url()
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""
                SELECT reminder_id, event_id, lease_id, tenant_id,
                       channel, recipient, reminder_type, message_body,
                       status, sent_at, error_message
                FROM renewal_reminders
                WHERE lease_id = %s
                ORDER BY sent_at ASC;
            """, (lease_id,))
            rows = await cur.fetchall()
    return rows
