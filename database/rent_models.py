"""
Database layer for Rent Reminder & Escalation Workflows.
Supports SQLite / Postgres tenant record management.
"""
import sqlite3
import os
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def get_db_path(override_path: Optional[str] = None) -> str:
    if override_path:
        return override_path
    return os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "elarion.db"))

CREATE_TENANTS_TABLE_SQL = """

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id           TEXT PRIMARY KEY,
    property_id         TEXT NOT NULL,
    tenant_name         TEXT NOT NULL,
    tenant_phone        TEXT NOT NULL,
    property_address    TEXT NOT NULL,
    joining_date        TEXT DEFAULT NULL,  -- YYYY-MM-DD
    rent_due_date       TEXT NOT NULL,  -- YYYY-MM-DD
    last_payment_date   TEXT,           -- YYYY-MM-DD
    rent_amount         REAL NOT NULL,
    payment_status      TEXT DEFAULT 'overdue', -- active, due_soon, overdue, reminder_sent, followup_sent, escalated, paid
    reminder_30_sent_at TEXT DEFAULT NULL,      -- ISO Timestamp
    reminder_5_sent_at  TEXT DEFAULT NULL,      -- ISO Timestamp
    response_received   BOOLEAN DEFAULT 0,
    human_escalated     BOOLEAN DEFAULT 0,
    escalation_reason   TEXT DEFAULT NULL,
    manual_hold         BOOLEAN DEFAULT 0,
    last_reminder_status TEXT DEFAULT 'none',    -- none, reminder_sent, followup_sent, escalated
    created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at          TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

def init_rent_db(db_path: Optional[str] = None):
    """Initializes the tenants table in the database and ensures schema migrations."""
    target_path = get_db_path(db_path)
    conn = sqlite3.connect(target_path)
    cursor = conn.cursor()
    cursor.execute(CREATE_TENANTS_TABLE_SQL)
    
    # Auto-migration: Check if joining_date column exists
    cursor.execute("PRAGMA table_info(tenants);")
    columns = [row[1] for row in cursor.fetchall()]
    if "joining_date" not in columns:
        cursor.execute("ALTER TABLE tenants ADD COLUMN joining_date TEXT DEFAULT NULL;")
        logger.info("Migrated tenants table: Added missing joining_date column.")

    conn.commit()
    conn.close()
    logger.info(f"Initialized tenants table in {target_path}")

def seed_sample_tenants(db_path: Optional[str] = None):
    """Seeds test tenant records for workflow verification."""
    target_path = get_db_path(db_path)
    init_rent_db(target_path)
    conn = sqlite3.connect(target_path)
    cursor = conn.cursor()

    # Clear existing test tenants to ensure idempotent seed
    cursor.execute("DELETE FROM tenants;")

    sample_tenants = [
        # Candidate 1: Ali Ahmed - Joined 2026-07-01 (Day 1). Billing cycle 30th day = 2026-07-30. Overdue on 2026-08-05 -> Should get 30-Day Reminder #1
        (
            "T-101", "P-201", "Ali Ahmed", "0300-1112223", "Flat 4B, Gulberg Heights, Lahore",
            "2026-07-01", "2026-07-31", None, 75000.0, "overdue", None, None, 0, 0, None, 0, "none"
        ),
        # Candidate 2: Furqan Khan - Joined 2026-07-11 (Day 11). Billing cycle 30th day = 2026-08-10.
        # Reminder #1 sent on 2026-08-01, current date 2026-08-05 (Days 31-35 window) -> Should get Followup (31-35 Days Unpaid Warning)
        (
            "T-102", "P-202", "Furqan Khan", "0321-4445556", "Villa 12, DHA Phase 5, Lahore",
            "2026-07-11", "2026-08-10", None, 120000.0, "reminder_sent", "2026-08-01T08:00:00", None, 0, 0, None, 0, "reminder_sent"
        ),
        # Candidate 3: Hamza Malik - Joined 2026-06-20. Current date 2026-08-05 (Day 36+ unpaid past Day 35) -> Should ESCALATE to human
        (
            "T-103", "P-203", "Hamza Malik", "0333-7778889", "Apartment 302, F-10, Islamabad",
            "2026-06-20", "2026-07-20", None, 95000.0, "followup_sent", "2026-07-20T08:00:00", "2026-07-26T08:00:00", 0, 0, None, 0, "followup_sent"
        ),
        # Candidate 4: Usman Tariq - Manual hold active -> Should SKIP
        (
            "T-104", "P-204", "Usman Tariq", "0345-9990001", "House 88, Bahria Town, Karachi",
            "2026-06-15", "2026-07-15", None, 110000.0, "overdue", None, None, 0, 0, None, 1, "none"
        ),
        # Candidate 5: Sana Farooq - Paid tenant -> Should SKIP
        (
            "T-105", "P-205", "Sana Farooq", "0311-2223334", "Studio 15, Clifton, Karachi",
            "2026-07-01", "2026-08-01", "2026-08-02", 50000.0, "paid", None, None, 0, 0, None, 0, "none"
        ),
    ]

    cursor.executemany("""
        INSERT INTO tenants (
            tenant_id, property_id, tenant_name, tenant_phone, property_address,
            joining_date, rent_due_date, last_payment_date, rent_amount, payment_status,
            reminder_30_sent_at, reminder_5_sent_at, response_received,
            human_escalated, escalation_reason, manual_hold, last_reminder_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, sample_tenants)

    conn.commit()
    conn.close()
    logger.info(f"Seeded 5 sample tenant records successfully in {target_path}.")

def get_unpaid_overdue_tenants(ref_date_str: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Queries all tenant records where payment_status != 'paid' and rent_due_date <= ref_date or rent is due/overdue.
    """
    target_path = get_db_path(db_path)
    init_rent_db(target_path)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT * FROM tenants
        WHERE payment_status != 'paid'
          AND (rent_due_date <= ? OR joining_date IS NOT NULL);
    """
    cursor.execute(query, (ref_date_str,))
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

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
):
    """Updates reminder timestamps and status flags for a tenant."""
    target_path = get_db_path(db_path)
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
    logger.info(f"Updated tenant {tenant_id}: last_reminder_status={last_reminder_status} in {target_path}")

def get_tenant_by_id(tenant_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single tenant record by ID."""
    target_path = get_db_path(db_path)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tenants WHERE tenant_id = ?;", (tenant_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

