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


# ── Tool: lookup_tenant_by_name ───────────────────────────────────────
@mcp.tool()
async def lookup_tenant_by_name(name: str) -> str:
    """
    Look up a tenant by exact name (case-insensitive).
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
                WHERE  t.name ILIKE %s
                """,
                (name,),
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


# ── Tool: lookup_tenant_by_unit ───────────────────────────────────────
@mcp.tool()
async def lookup_tenant_by_unit(unit_id: str) -> str:
    """
    Look up a tenant by their unit_id, unit_number, or mention (e.g. 'Unit 204', '204', 'U-204').
    Returns tenant_id, name, unit_id, and property_id.
    """
    if not unit_id:
        return json.dumps({"error": "Unit not specified"})

    import re
    clean_val = str(unit_id).strip()
    norm = re.sub(r'(?i)^(unit|apt|apartment|house|flat|u)[\s\-#]*', '', clean_val).strip()

    db_pool = await get_pool()
    async with db_pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT t.tenant_id, t.name, u.unit_id, u.property_id
                FROM   units u
                LEFT JOIN tenants t ON t.unit_id = u.unit_id
                WHERE  u.unit_id ILIKE %s
                   OR  u.unit_number ILIKE %s
                   OR  u.unit_id ILIKE %s
                   OR  u.unit_number ILIKE %s
                   OR  %s ILIKE '%%' || u.unit_number || '%%'
                   OR  %s ILIKE '%%' || u.unit_id || '%%'
                ORDER BY t.tenant_id NULLS LAST
                LIMIT 1
                """,
                (clean_val, clean_val, f"%{norm}%", f"%{norm}%", clean_val, clean_val),
            )
            row = await cur.fetchone()

    if row:
        fallback_tenant_id = row[0] or f"T-{row[2].replace('U-', '') if row[2] else 'GUEST'}"
        return json.dumps({
            "tenant_id":   fallback_tenant_id,
            "name":        row[1] or "Resident",
            "unit_id":     row[2],
            "property_id": row[3],
        })
    return json.dumps({"error": "Tenant / Unit not found"})


# ── Tool: lookup_property ─────────────────────────────────────────────
@mcp.tool()
async def lookup_property(unit_id: str) -> str:
    """
    Look up a property by unit_id or unit_number (joins units to properties).
    Returns unit_id, property_id, address, unit_number.
    """
    if not unit_id:
        return json.dumps({"error": "Unit not specified"})

    import re
    clean_val = str(unit_id).strip()
    norm = re.sub(r'(?i)^(unit|apt|apartment|house|flat|u)[\s\-#]*', '', clean_val).strip()

    db_pool = await get_pool()
    async with db_pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT u.unit_id, u.property_id, p.address, u.unit_number
                FROM   units      u
                JOIN   properties p ON p.property_id = u.property_id
                WHERE  u.unit_id ILIKE %s
                   OR  u.unit_number ILIKE %s
                   OR  u.unit_id ILIKE %s
                   OR  u.unit_number ILIKE %s
                   OR  %s ILIKE '%%' || u.unit_number || '%%'
                   OR  %s ILIKE '%%' || u.unit_id || '%%'
                LIMIT 1
                """,
                (clean_val, clean_val, f"%{norm}%", f"%{norm}%", clean_val, clean_val),
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


# ── Internal helper — log one assignment attempt row ──────────────────
async def _log_attempt(cur, ticket_id: str, vendor_id, strategy: str, result: str, reason: str) -> None:
    await cur.execute(
        """
        INSERT INTO assignment_attempts (ticket_id, vendor_id, strategy_used, result, reason)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (ticket_id, vendor_id, strategy, result, reason),
    )
    print(f"[ASSIGNMENT ATTEMPT] {strategy} -> {result} ({reason})", file=sys.stderr)


# ── Tool: assign_vendor ─────────────────────────────────────────────────
@mcp.tool()
async def assign_vendor(
    ticket_id:   str,
    category:    str,
    property_id: str,
    urgency:     str,
) -> str:
    """
    Run the vendor assignment routing engine for a ticket, following strategy order:

    1. Preferred/Contracted  — vendor with is_contracted=TRUE for this property_id + category
    2. Emergency priority    — if urgency="emergency" (case-insensitive), restrict candidate pool to accepts_emergency=TRUE
    3. Skill filter          — category match is mandatory at every step
    4. Location-based        — rank remaining candidates by service_area match to property_id
    5. Availability filter   — deprioritize/exclude vendors where active_jobs >= capacity
    6. Fallback/On-call pool — vendors with service_area='FALLBACK_POOL'
    7. Exhausted              — no candidate found anywhere -> NEEDS_MANUAL_ASSIGNMENT

    Every step taken is written to assignment_attempts for audit/coordinator visibility.
    Does NOT commit the assignment — only proposes a candidate. Call commit_assignment
    after human approval.
    """
    try:
        db_pool = await get_pool()
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:

                # ── Strategy 1: Preferred / Contracted vendor ──────────────
                await cur.execute(
                    """
                    SELECT vendor_id, name, phone, category, service_area,
                           accepts_emergency, capacity, active_jobs
                    FROM   vendors
                    WHERE  contracted_property_id = %s
                      AND  category = %s
                      AND  is_contracted = TRUE
                      AND  active = TRUE
                    """,
                    (property_id, category),
                )
                contracted = await cur.fetchone()

                # Normalize once: callers may pass "emergency", "Emergency", etc.
                # This used to compare against the exact string "EMERGENCY", which
                # the priority_detection_node keyword net never actually sent
                # (it used lowercase "emergency") -- so genuinely urgent tickets
                # were silently skipping emergency-vendor treatment. Comparing
                # case-insensitively here matches the unified low/medium/high/
                # emergency label set used across the whole project now.
                is_emergency = (urgency or "").strip().lower() == "emergency"

                if contracted and contracted[7] < contracted[6]:
                    # capacity check (active_jobs < capacity) — otherwise fall through
                    if not (is_emergency and not contracted[5]):
                        await _log_attempt(cur, ticket_id, contracted[0], "CONTRACTED", "MATCHED",
                                            "Contracted vendor available and within capacity")
                        await conn.commit()
                        return json.dumps({
                            "status": "matched", "strategy": "CONTRACTED",
                            "vendor": {"vendor_id": contracted[0], "name": contracted[1],
                                       "phone": contracted[2], "category": contracted[3]},
                        })

                if contracted:
                    await _log_attempt(cur, ticket_id, contracted[0], "CONTRACTED", "SKIPPED",
                                        "Contracted vendor over capacity or cannot take emergency job")
                else:
                    await _log_attempt(cur, ticket_id, None, "CONTRACTED", "NO_CANDIDATE",
                                        "No contracted vendor for this property/category")

                # ── Strategy 3+4+5: Skill filter (always) + Location + Availability ──
                # Emergency urgency restricts to accepts_emergency=TRUE vendors (Strategy 2)
                base_query = """
                    SELECT vendor_id, name, phone, category, service_area,
                           accepts_emergency, capacity, active_jobs
                    FROM   vendors
                    WHERE  category = %s
                      AND  active = TRUE
                      AND  service_area = %s
                      AND  active_jobs < capacity
                """
                params = [category, property_id]
                if is_emergency:
                    base_query += " AND accepts_emergency = TRUE"
                base_query += " ORDER BY active_jobs ASC"

                await cur.execute(base_query, tuple(params))
                candidates = await cur.fetchall()

                if candidates:
                    top = candidates[0]
                    strategy_label = "EMERGENCY_BROADCAST" if is_emergency else "LOCATION_BASED"
                    await _log_attempt(cur, ticket_id, top[0], strategy_label, "MATCHED",
                                        f"Skill+location+availability match, {len(candidates)} candidate(s) found")
                    await conn.commit()
                    return json.dumps({
                        "status": "matched", "strategy": strategy_label,
                        "vendor": {"vendor_id": top[0], "name": top[1],
                                   "phone": top[2], "category": top[3]},
                    })

                await _log_attempt(cur, ticket_id, None, "LOCATION_BASED", "NO_CANDIDATE",
                                    "No skilled/available vendor found in service area")

                # ── Strategy 6: Fallback / On-call pool ─────────────────────
                # Skill filter (category) is ALWAYS applied, even in the fallback pool —
                # an on-call marketplace vendor still has to actually carry the right skill tag.
                fallback_query = """
                    SELECT vendor_id, name, phone, category, service_area,
                           accepts_emergency, capacity, active_jobs
                    FROM   vendors
                    WHERE  service_area = 'FALLBACK_POOL'
                      AND  category = %s
                      AND  active = TRUE
                      AND  active_jobs < capacity
                """
                fallback_params = [category]
                if is_emergency:
                    fallback_query += " AND accepts_emergency = TRUE"
                fallback_query += " ORDER BY active_jobs ASC"

                await cur.execute(fallback_query, tuple(fallback_params))
                fallback = await cur.fetchone()

                if fallback:
                    await _log_attempt(cur, ticket_id, fallback[0], "FALLBACK_POOL", "MATCHED",
                                        "On-call pool vendor assigned")
                    await conn.commit()
                    return json.dumps({
                        "status": "matched", "strategy": "FALLBACK_POOL",
                        "vendor": {"vendor_id": fallback[0], "name": fallback[1],
                                   "phone": fallback[2], "category": fallback[3]},
                    })

                # ── Strategy 7: Exhausted ────────────────────────────────────
                await _log_attempt(cur, ticket_id, None, "EXHAUSTED", "NO_CANDIDATE",
                                    "All strategies exhausted, no vendor available")
                await cur.execute(
                    "UPDATE maintenance_tickets SET assignment_status = 'NEEDS_MANUAL_ASSIGNMENT' WHERE ticket_id = %s",
                    (ticket_id,),
                )
                await conn.commit()

                # Pull attempt history for the coordinator
                await cur.execute(
                    "SELECT strategy_used, result, reason, timestamp FROM assignment_attempts "
                    "WHERE ticket_id = %s ORDER BY timestamp ASC",
                    (ticket_id,),
                )
                history_rows = await cur.fetchall()
                history = [
                    {"strategy": r[0], "result": r[1], "reason": r[2], "timestamp": str(r[3])}
                    for r in history_rows
                ]

                return json.dumps({
                    "status": "needs_manual_assignment",
                    "strategy": "EXHAUSTED",
                    "attempt_history": history,
                })

    except psycopg.Error as e:
        return json.dumps({"status": "error", "message": f"Database error: {str(e)}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Server error: {str(e)}"})


# ── Tool: commit_assignment ──────────────────────────────────────────────
@mcp.tool()
async def commit_assignment(
    ticket_id:   str,
    vendor_id:   str,
    approved_by: str = "human_coordinator",
) -> str:
    """
    Commit a vendor assignment AFTER human approval.
    Updates ticket status to ASSIGNED, increments vendor active_jobs, writes audit log.
    Only call this after the human has explicitly approved the proposed vendor.
    """
    try:
        db_pool = await get_pool()
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:

                await cur.execute(
                    "SELECT ticket_id, assignment_status FROM maintenance_tickets WHERE ticket_id = %s",
                    (ticket_id,),
                )
                ticket_row = await cur.fetchone()
                if not ticket_row:
                    return json.dumps({"status": "error", "message": f"Ticket {ticket_id} not found"})

                before_state = {"assignment_status": ticket_row[1]}

                await cur.execute(
                    "UPDATE maintenance_tickets SET vendor_id = %s, assignment_status = 'ASSIGNED' "
                    "WHERE ticket_id = %s",
                    (vendor_id, ticket_id),
                )
                await cur.execute(
                    "UPDATE vendors SET active_jobs = active_jobs + 1 WHERE vendor_id = %s",
                    (vendor_id,),
                )

                after_state = {"ticket_id": ticket_id, "vendor_id": vendor_id, "assignment_status": "ASSIGNED"}
                await _write_audit_log(
                    cur,
                    action="ASSIGN_VENDOR",
                    details=f"Ticket {ticket_id} assigned to vendor {vendor_id}, approved by {approved_by}",
                    actor=approved_by,
                    before_state=before_state,
                    after_state=after_state,
                )

                await conn.commit()

            return json.dumps({"status": "success", "ticket_id": ticket_id,
                                "vendor_id": vendor_id, "assignment_status": "ASSIGNED"})
    except psycopg.Error as e:
        return json.dumps({"status": "error", "message": f"Database error: {str(e)}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Server error: {str(e)}"})


# ── Entry point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
