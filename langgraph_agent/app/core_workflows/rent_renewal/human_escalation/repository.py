"""
Human Escalation Repository — Phase 5, Workflow #4.

Database access for storing human escalations, updating manager actions,
and recording audit trail events. Enforces idempotency to prevent duplicate active escalations.
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


async def create_escalation(
    lease_id: str,
    tenant_id: str,
    property_id: str,
    escalation_reason: str,
    escalation_priority: str = "MEDIUM",
    description: Optional[str] = None,
    assigned_to: str = "Property Manager",
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Creates an escalation record in human_escalations idempotently.
    If an OPEN escalation for this lease and reason already exists, returns existing escalation_id.
    """
    db_url = _get_db_url()
    meta_json = json.dumps(metadata or {})

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            # 1. Idempotency check: check if an active escalation already exists
            await cur.execute("""
                SELECT escalation_id FROM human_escalations
                WHERE lease_id = %s AND escalation_reason = %s AND status IN ('OPEN', 'PENDING_MANAGER_ACTION')
                LIMIT 1;
            """, (lease_id, escalation_reason))
            existing = await cur.fetchone()

            if existing:
                logger.info("Found existing active escalation #%d for lease %s (%s). Skipping duplicate.",
                            existing["escalation_id"], lease_id, escalation_reason)
                return existing["escalation_id"]

            # 2. Insert new escalation record
            await cur.execute("""
                INSERT INTO human_escalations (
                    lease_id, tenant_id, property_id, escalation_reason,
                    escalation_priority, status, description, assigned_to,
                    notified_at, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, 'OPEN', %s, %s, CURRENT_TIMESTAMP, %s::jsonb
                ) RETURNING escalation_id;
            """, (
                lease_id,
                tenant_id,
                property_id,
                escalation_reason,
                escalation_priority,
                description or "",
                assigned_to,
                meta_json,
            ))
            row = await cur.fetchone()
            escalation_id = row["escalation_id"]

            # 3. Log audit event
            await cur.execute("""
                INSERT INTO escalation_audit_logs (
                    escalation_id, lease_id, tenant_id, event_type, actor, details
                ) VALUES (
                    %s, %s, %s, 'ESCALATION_CREATED', 'system', %s::jsonb
                );
            """, (escalation_id, lease_id, tenant_id, json.dumps({
                "reason": escalation_reason,
                "priority": escalation_priority,
                "assigned_to": assigned_to,
            })))

        await conn.commit()

    logger.info("Created human escalation #%d for lease %s [reason=%s, priority=%s]",
                escalation_id, lease_id, escalation_reason, escalation_priority)
    return escalation_id


async def get_active_escalation(lease_id: str) -> Optional[Dict[str, Any]]:
    """Queries any active/open escalation for a lease."""
    db_url = _get_db_url()
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""
                SELECT * FROM human_escalations
                WHERE lease_id = %s AND status IN ('OPEN', 'PENDING_MANAGER_ACTION')
                ORDER BY created_at DESC
                LIMIT 1;
            """, (lease_id,))
            row = await cur.fetchone()
    return row


async def record_manager_decision(
    escalation_id: int,
    manager_action: str,
    manager_notes: Optional[str] = None,
    new_status: str = "RESOLVED",
    actor: str = "Property Manager",
) -> None:
    """
    Records an authorized manager decision and updates escalation resolution state.
    """
    db_url = _get_db_url()
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                UPDATE human_escalations
                SET manager_action = %s,
                    manager_notes = %s,
                    status = %s,
                    resolved_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE escalation_id = %s;
            """, (manager_action, manager_notes or "", new_status, escalation_id))

            await cur.execute("""
                INSERT INTO escalation_audit_logs (
                    escalation_id, event_type, actor, details
                ) VALUES (
                    %s, 'MANAGER_ACTION_RECEIVED', %s, %s::jsonb
                );
            """, (escalation_id, actor, json.dumps({
                "action": manager_action,
                "notes": manager_notes,
                "status": new_status,
            })))
        await conn.commit()

    logger.info("Recorded manager decision for escalation #%d: action=%s status=%s",
                escalation_id, manager_action, new_status)
