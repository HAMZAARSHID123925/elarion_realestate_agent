"""
Renewal Intent Repository — Phase 3, Workflow #4.

Database access for storing interpreted tenant renewal intents
and creating manager review notifications.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List

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


async def record_renewal_intent(
    lease_id: str,
    tenant_id: str,
    tenant_response: str,
    intent: str,
    confidence: float,
    reasoning: str,
    renewal_status: str,
    requested_term: Optional[int] = None,
    proposed_rent: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Inserts an interpreted renewal intent record into renewal_intents.
    Returns the generated intent_id.
    """
    db_url = _get_db_url()
    meta_json = json.dumps(metadata or {})

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                INSERT INTO renewal_intents (
                    lease_id, tenant_id, tenant_response, intent,
                    confidence, reasoning, renewal_status,
                    requested_term, proposed_rent, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
                ) RETURNING intent_id;
            """, (
                lease_id,
                tenant_id,
                tenant_response,
                intent,
                confidence,
                reasoning,
                renewal_status,
                requested_term,
                proposed_rent,
                meta_json,
            ))
            row = await cur.fetchone()
            intent_id = row[0]
        await conn.commit()
    logger.info("Recorded renewal intent #%d: lease=%s intent=%s", intent_id, lease_id, intent)
    return intent_id


async def create_manager_notification(
    notification_type: str,
    lease_id: str,
    tenant_id: str,
    property_id: str,
    title: str,
    details: Optional[Dict[str, Any]] = None,
    assigned_to: str = "Property Manager",
) -> int:
    """
    Inserts a manager review task into manager_notifications.
    Returns the created notification_id.
    """
    db_url = _get_db_url()
    details_json = json.dumps(details or {})

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                INSERT INTO manager_notifications (
                    notification_type, lease_id, tenant_id, property_id,
                    title, status, details, assigned_to
                ) VALUES (
                    %s, %s, %s, %s, %s, 'PENDING', %s::jsonb, %s
                ) RETURNING notification_id;
            """, (
                notification_type,
                lease_id,
                tenant_id,
                property_id,
                title,
                details_json,
                assigned_to,
            ))
            row = await cur.fetchone()
            notif_id = row[0]
        await conn.commit()
    logger.info("Created manager notification #%d: [%s] %s", notif_id, notification_type, title)
    return notif_id


async def get_latest_intent(lease_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the most recent renewal intent record for a lease."""
    db_url = _get_db_url()
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""
                SELECT * FROM renewal_intents
                WHERE lease_id = %s
                ORDER BY created_at DESC
                LIMIT 1;
            """, (lease_id,))
            row = await cur.fetchone()
    return row
