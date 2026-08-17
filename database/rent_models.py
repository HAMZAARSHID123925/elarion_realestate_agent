"""
Database adapter layer for Rent Reminder & Escalation Workflows — Phase 2 Unified.

Provides unified data access for tenant records, delegating to the canonical
PostgreSQL TenantRepository (via DATABASE_URL) while maintaining fallback compatibility
for isolated local test fixtures (via SQLite DB_PATH).
"""
import os
import sys
import sqlite3
import asyncio
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

# Ensure workspace root is on sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from database.tenant_repository import tenant_repository, TenantRepository

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Safely runs an async coroutine from synchronous calling contexts."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def get_db_path(override_path: Optional[str] = None) -> Optional[str]:
    """Returns local DB path if configured, else None (indicating PostgreSQL default)."""
    if override_path:
        return override_path
    return os.environ.get("DB_PATH")


CREATE_TENANTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id           TEXT PRIMARY KEY,
    property_id         TEXT NOT NULL,
    tenant_name         TEXT NOT NULL,
    tenant_phone        TEXT NOT NULL,
    property_address    TEXT NOT NULL,
    rent_due_date       TEXT NOT NULL,
    last_payment_date   TEXT,
    rent_amount         REAL NOT NULL,
    payment_status      TEXT DEFAULT 'overdue',
    reminder_30_sent_at TEXT DEFAULT NULL,
    reminder_5_sent_at  TEXT DEFAULT NULL,
    response_received   BOOLEAN DEFAULT 0,
    human_escalated     BOOLEAN DEFAULT 0,
    escalation_reason   TEXT DEFAULT NULL,
    manual_hold         BOOLEAN DEFAULT 0,
    last_reminder_status TEXT DEFAULT 'none',
    created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at          TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def init_rent_db(db_path: Optional[str] = None):
    """Initializes the tenants table in the target database."""
    target_path = get_db_path(db_path)
    if target_path:
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        cursor.execute(CREATE_TENANTS_TABLE_SQL)
        conn.commit()
        conn.close()
        logger.info(f"Initialized local tenants table in {target_path}")
    else:
        logger.info("PostgreSQL database initialized via migrations (000_init_base_tables.sql)")


def seed_sample_tenants(db_path: Optional[str] = None):
    """Seeds test tenant records for workflow verification."""
    target_path = get_db_path(db_path)
    if target_path:
        init_rent_db(target_path)
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tenants;")

        sample_tenants = [
            (
                "T-101", "P-201", "Ali Ahmed", "0300-1112223", "Flat 4B, Gulberg Heights, Lahore",
                "2026-07-06", None, 75000.0, "overdue", None, None, 0, 0, None, 0, "none"
            ),
            (
                "T-102", "P-202", "Zainab Bibi", "0321-4445556", "Villa 12, DHA Phase 5, Lahore",
                "2026-06-25", None, 120000.0, "reminder_sent", "2026-07-31T08:00:00", None, 0, 0, None, 0, "reminder_sent"
            ),
            (
                "T-103", "P-203", "Hamza Malik", "0333-7778889", "Apartment 302, F-10, Islamabad",
                "2026-06-20", None, 95000.0, "followup_sent", "2026-07-25T08:00:00", "2026-08-03T08:00:00", 0, 0, None, 0, "followup_sent"
            ),
            (
                "T-104", "P-204", "Usman Tariq", "0345-9990001", "House 88, Bahria Town, Karachi",
                "2026-06-15", None, 110000.0, "overdue", None, None, 0, 0, None, 1, "none"
            ),
            (
                "T-105", "P-205", "Sana Farooq", "0311-2223334", "Studio 15, Clifton, Karachi",
                "2026-07-01", "2026-07-02", 50000.0, "paid", None, None, 0, 0, None, 0, "none"
            ),
        ]

        cursor.executemany("""
            INSERT INTO tenants (
                tenant_id, property_id, tenant_name, tenant_phone, property_address,
                rent_due_date, last_payment_date, rent_amount, payment_status,
                reminder_30_sent_at, reminder_5_sent_at, response_received,
                human_escalated, escalation_reason, manual_hold, last_reminder_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, sample_tenants)

        conn.commit()
        conn.close()
        logger.info(f"Seeded 5 sample tenant records in {target_path}")
    else:
        logger.info("Using PostgreSQL canonical database seed from migration 000.")


def get_unpaid_overdue_tenants(ref_date_str: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Queries all tenant records where payment_status != 'paid' and rent_due_date < ref_date.
    Uses canonical PostgreSQL TenantRepository, falling back to local SQLite when db_path is specified.
    """
    target_path = get_db_path(db_path)
    if target_path:
        init_rent_db(target_path)
        conn = sqlite3.connect(target_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM tenants WHERE payment_status != 'paid' AND rent_due_date < ?;"
        cursor.execute(query, (ref_date_str or date.today().isoformat(),))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    return _run_async(tenant_repository.get_unpaid_overdue_tenants(ref_date_str))


def update_tenant_reminder_status(
    tenant_id: str,
    last_reminder_status: str,
    reminder_30_sent_at: Optional[str] = None,
    reminder_5_sent_at: Optional[str] = None,
    human_escalated: Optional[bool] = None,
    escalation_reason: Optional[str] = None,
    payment_status: Optional[str] = None,
    response_received: Optional[bool] = None,
    db_path: Optional[str] = None
) -> bool:
    """
    Updates reminder timestamps and status flags for a tenant.
    Uses canonical PostgreSQL TenantRepository, falling back to local SQLite when db_path is specified.
    """
    target_path = get_db_path(db_path)
    if target_path:
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()

        updates = ["last_reminder_status = ?, updated_at = CURRENT_TIMESTAMP"]
        params = [last_reminder_status]

        if reminder_30_sent_at is not None:
            updates.append("reminder_30_sent_at = ?")
            params.append(reminder_30_sent_at)
        if reminder_5_sent_at is not None:
            updates.append("reminder_5_sent_at = ?")
            params.append(reminder_5_sent_at)
        if human_escalated is not None:
            updates.append("human_escalated = ?")
            params.append(1 if human_escalated else 0)
        if escalation_reason is not None:
            updates.append("escalation_reason = ?")
            params.append(escalation_reason)
        if payment_status is not None:
            updates.append("payment_status = ?")
            params.append(payment_status)
        if response_received is not None:
            updates.append("response_received = ?")
            params.append(1 if response_received else 0)

        params.append(tenant_id)
        sql = f"UPDATE tenants SET {', '.join(updates)} WHERE tenant_id = ?;"
        cursor.execute(sql, params)
        conn.commit()
        conn.close()
        return True

    return _run_async(tenant_repository.update_reminder_status(
        tenant_id=tenant_id,
        last_reminder_status=last_reminder_status,
        reminder_30_sent_at=reminder_30_sent_at,
        reminder_5_sent_at=reminder_5_sent_at,
        human_escalated=human_escalated,
        escalation_reason=escalation_reason,
        payment_status=payment_status,
        response_received=response_received
    ))


def get_tenant_by_id(tenant_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single tenant record by ID.
    Uses canonical PostgreSQL TenantRepository, falling back to local SQLite when db_path is specified.
    """
    target_path = get_db_path(db_path)
    if target_path:
        conn = sqlite3.connect(target_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tenants WHERE tenant_id = ?;", (tenant_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    return _run_async(tenant_repository.get_tenant_by_id(tenant_id))
