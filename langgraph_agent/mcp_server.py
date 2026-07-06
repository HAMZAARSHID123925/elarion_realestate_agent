"""
MCP Server — Stage 3 (Real Postgres via psycopg async, stdio transport)

Windows note: psycopg async requires SelectorEventLoop, not ProactorEventLoop.
We force this before FastMCP starts its own loop.
"""

import os
import sys
import json
import uuid
import asyncio

# ── Force SelectorEventLoop on Windows BEFORE anything asyncio-related ──
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
import psycopg
from psycopg_pool import AsyncConnectionPool
from mcp.server.fastmcp import FastMCP

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment.")

# ── MCP server ────────────────────────────────────────────────────────
mcp = FastMCP("MaintenanceServer")


# ── DB helper: Async Connection Pool ──────────────────────────────────
pool = None

async def get_pool():
    global pool
    if pool is None:
        pool = AsyncConnectionPool(conninfo=DATABASE_URL, min_size=1, max_size=5, open=False)
        await pool.open()
    return pool


# ── Internal helper — NOT exposed as an MCP tool ──────────────────────
async def _write_audit_log(cur, action: str, details: str, actor: str,
                            before_state, after_state) -> None:
    """Write an audit row inside the caller's cursor/transaction."""
    await cur.execute(
        """
        INSERT INTO audit_logs (action, details, actor, before_state, after_state)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            action,
            details,
            actor,
            json.dumps(before_state) if before_state else None,
            json.dumps(after_state)  if after_state  else None,
        ),
    )
    print(f"[AUDIT LOG] {actor} | {action}: {details}", file=sys.stderr)


# ── Tool: lookup_tenant ───────────────────────────────────────────────
@mcp.tool()
async def lookup_tenant(phone_or_email: str) -> str:
    """
    Look up a tenant by phone number or email.
    Returns tenant_id, name, unit_id, and property_id (resolved via unit join).
    """
    db_pool = await get_pool()
    async with db_pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT t.tenant_id, t.name, t.unit_id, u.property_id
                FROM   tenants t
                JOIN   units   u ON u.unit_id = t.unit_id
                WHERE  t.phone_or_email = %s
                """,
                (phone_or_email,),
            )
            row = await cur.fetchone()

    if row:
        return json.dumps({
            "tenant_id":   row[0],
            "name":        row[1],
            "unit_id":     row[2],
            "property_id": row[3],
        })
    return json.dumps({"error": "Tenant not found"})


# ── Tool: lookup_property ─────────────────────────────────────────────
@mcp.tool()
async def lookup_property(unit_id: str) -> str:
    """
    Look up a property by unit_id (joins units to properties).
    Returns unit_id, property_id, address, unit_number.
    """
    db_pool = await get_pool()
    async with db_pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT u.unit_id, u.property_id, p.address, u.unit_number
                FROM   units      u
                JOIN   properties p ON p.property_id = u.property_id
                WHERE  u.unit_id = %s
                """,
                (unit_id,),
            )
            row = await cur.fetchone()

    if row:
        return json.dumps({
            "unit_id":     row[0],
            "property_id": row[1],
            "address":     row[2],
            "unit_number": row[3],
        })
    return json.dumps({"error": "Unit / property not found"})


# ── Tool: create_ticket ───────────────────────────────────────────────
@mcp.tool()
async def create_ticket(
    tenant_id:           str,
    unit_id:             str,
    category:            str,
    description:         str,
    urgency:             str,
    permission_to_enter: str,
    pets_present:        str,
    idempotency_key:     str,
    source_channel:      str = "voice",
    created_by:          str = "system",
) -> str:
    """
    Create a maintenance ticket against Postgres.

    Guarantees:
    - Idempotency  : same idempotency_key returns existing ticket without a new row.
    - Duplicate    : rejects if an OPEN ticket already exists for unit+category.
    - Audit        : writes audit_logs row inside the same transaction.
    - property_id  : resolved from unit_id (tenant -> unit -> property join).
    """
    try:
        db_pool = await get_pool()
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:

                # 1 -- Idempotency check ----------------------------------
                await cur.execute(
                    "SELECT ticket_id FROM maintenance_tickets WHERE idempotency_key = %s",
                    (idempotency_key,),
                )
                existing = await cur.fetchone()
                if existing:
                    ticket_id = existing[0]
                    await _write_audit_log(
                        cur,
                        action="CREATE_TICKET_IDEMPOTENT",
                        details=f"Idempotent replay for key {idempotency_key} -> ticket {ticket_id}",
                        actor=created_by,
                        before_state=None,
                        after_state={"ticket_id": ticket_id},
                    )
                    await conn.commit()
                    # Fetch full row to return
                    await cur.execute(
                        "SELECT ticket_id, tenant_id, unit_id, category, urgency, status "
                        "FROM maintenance_tickets WHERE ticket_id = %s",
                        (ticket_id,),
                    )
                    row = await cur.fetchone()
                    return json.dumps({
                        "status": "success",
                        "idempotent": True,
                        "ticket": {
                            "ticket_id": row[0], "tenant_id": row[1],
                            "unit_id":   row[2], "category":  row[3],
                            "urgency":   row[4], "status":    row[5],
                        },
                    })
    
                # 2 -- Duplicate open-ticket check ------------------------
                await cur.execute(
                    """
                    SELECT ticket_id FROM maintenance_tickets
                    WHERE  unit_id = %s AND category = %s AND status = 'OPEN'
                    """,
                    (unit_id, category),
                )
                dup = await cur.fetchone()
                if dup:
                    dup_id = dup[0]
                    await _write_audit_log(
                        cur,
                        action="CREATE_TICKET_DUPLICATE",
                        details=f"Duplicate OPEN ticket {dup_id} for unit {unit_id}, category {category}",
                        actor=created_by,
                        before_state=None,
                        after_state={"existing_ticket_id": dup_id},
                    )
                    await conn.commit()
                    return json.dumps({
                        "status": "duplicate",
                        "message": (
                            f"An open ticket for '{category}' already exists at "
                            f"unit {unit_id}. Would you like to attach a note to it instead?"
                        ),
                        "existing_ticket_id": dup_id,
                    })
    
                # 3 -- Resolve property_id --------------------------------
                await cur.execute(
                    "SELECT property_id FROM units WHERE unit_id = %s", (unit_id,)
                )
                prop_row    = await cur.fetchone()
                property_id = prop_row[0] if prop_row else None
    
                # 4 -- Insert new ticket ----------------------------------
                new_id = f"TKT-{str(uuid.uuid4())[:8]}"
                await cur.execute(
                    """
                    INSERT INTO maintenance_tickets (
                        ticket_id, tenant_id, property_id, unit_id,
                        category, description, urgency,
                        permission_to_enter, pets_present,
                        status, source_channel, created_by, idempotency_key
                    ) VALUES (%s,%s,%s,%s, %s,%s,%s, %s,%s, 'OPEN',%s,%s,%s)
                    """,
                    (
                        new_id, tenant_id, property_id, unit_id,
                        category, description, urgency,
                        permission_to_enter, pets_present,
                        source_channel, created_by, idempotency_key,
                    ),
                )
    
                # 5 -- Audit log ------------------------------------------
                after_state = {
                    "ticket_id":   new_id,
                    "tenant_id":   tenant_id,
                    "unit_id":     unit_id,
                    "property_id": property_id,
                    "category":    category,
                    "urgency":     urgency,
                    "status":      "OPEN",
                }
                await _write_audit_log(
                    cur,
                    action="CREATE_TICKET_SUCCESS",
                    details=f"Ticket {new_id} created for unit {unit_id}, category {category}",
                    actor=created_by,
                    before_state=None,
                    after_state=after_state,
                )
    
                await conn.commit()
    
            return json.dumps({"status": "success", "idempotent": False, "ticket": after_state})
    except psycopg.Error as e:
        return json.dumps({"status": "error", "message": f"Database error: {str(e)}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Server error: {str(e)}"})


# ── Entry point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
