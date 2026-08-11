"""
Lease Expiry Repository — Phase 1, Workflow #4.

All database access for the lease expiry tracking service.
Uses psycopg (async) matching the project's existing init_db.py pattern.
Connects via DATABASE_URL.
"""
import os
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Set

import psycopg
from psycopg.rows import dict_row

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


def _get_db_url() -> str:
    """Returns DATABASE_URL, raising if not set."""
    url = DATABASE_URL or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url


async def get_active_leases() -> List[Dict[str, Any]]:
    """
    Query all leases with status = 'active'.

    Returns a list of dicts with keys:
        lease_id, tenant_id, property_id, lease_end_date, status
    """
    db_url = _get_db_url()
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""
                SELECT lease_id, tenant_id, property_id,
                       lease_end_date, status
                FROM leases
                WHERE status = 'active'
                ORDER BY lease_end_date ASC;
            """)
            rows = await cur.fetchall()
    return rows


async def get_existing_event_windows(lease_id: str) -> Set[int]:
    """
    Get the set of window_days values that already have events for a lease.

    Used for application-level dedup check (performance optimization;
    the DB unique constraint is the true safety net per Phase 1 §17).
    """
    db_url = _get_db_url()
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT window_days FROM lease_expiry_events WHERE lease_id = %s;",
                (lease_id,),
            )
            rows = await cur.fetchall()
    return {row[0] for row in rows}


async def insert_expiry_event(
    event_name: str,
    lease_id: str,
    tenant_id: str,
    property_id: str,
    expiry_date: date,
    days_remaining: int,
    window_days: int,
    event_date: date,
    run_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Insert a lease expiry event idempotently.

    Uses INSERT ... ON CONFLICT (lease_id, window_days) DO NOTHING
    to enforce the uniqueness constraint at the DB level (Phase 1 §17).

    Returns:
        True if a new row was inserted, False if it was a duplicate (conflict).
    """
    import json

    db_url = _get_db_url()
    meta_json = json.dumps(metadata or {})

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO lease_expiry_events
                    (event_name, lease_id, tenant_id, property_id,
                     expiry_date, days_remaining, window_days,
                     event_date, event_status, run_id, metadata)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', %s, %s::jsonb)
                ON CONFLICT (lease_id, window_days) DO NOTHING;
                """,
                (
                    event_name,
                    lease_id,
                    tenant_id,
                    property_id,
                    expiry_date,
                    days_remaining,
                    window_days,
                    event_date,
                    run_id,
                    meta_json,
                ),
            )
            inserted = cur.rowcount > 0
        await conn.commit()
    return inserted


async def create_scan_run(
    run_id: str,
    trigger_type: str = "manual",
    window_config: Optional[List[int]] = None,
) -> None:
    """Create a new scan run record in RUNNING status."""
    import json

    db_url = _get_db_url()
    config_json = json.dumps(window_config or [])

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO lease_expiry_scan_runs
                    (run_id, trigger_type, window_config, status)
                VALUES (%s, %s, %s::jsonb, 'RUNNING');
                """,
                (run_id, trigger_type, config_json),
            )
        await conn.commit()


async def update_scan_run(
    run_id: str,
    leases_scanned: int = 0,
    events_created: int = 0,
    duplicates_skipped: int = 0,
    errors_count: int = 0,
    status: str = "COMPLETED",
    error_details: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Update a scan run record with results."""
    import json

    db_url = _get_db_url()
    errors_json = json.dumps(error_details or [])

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE lease_expiry_scan_runs
                SET finished_at = CURRENT_TIMESTAMP,
                    leases_scanned = %s,
                    events_created = %s,
                    duplicates_skipped = %s,
                    errors_count = %s,
                    status = %s,
                    error_details = %s::jsonb
                WHERE run_id = %s;
                """,
                (
                    leases_scanned,
                    events_created,
                    duplicates_skipped,
                    errors_count,
                    status,
                    errors_json,
                    run_id,
                ),
            )
        await conn.commit()
