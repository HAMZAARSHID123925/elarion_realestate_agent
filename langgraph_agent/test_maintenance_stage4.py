"""
Stage 4 Integration Tests — Vendor Assignment Engine + Human-in-the-Loop Approval

Covers:
  - Test 1: Plumbing issue -> CONTRACTED vendor match -> human APPROVES -> ASSIGNED
  - Test 2: Electrical issue -> LOCATION_BASED match -> human REJECTS -> NEEDS_MANUAL_ASSIGNMENT
  - Test 3: Security issue -> zero vendors of that category anywhere (incl. fallback pool) -> EXHAUSTED
             (skips human approval entirely, straight to NEEDS_MANUAL_ASSIGNMENT)
             NOTE: "EMERGENCY" urgency in this codebase only ever comes from keyword-triggered
             priority_detection_node (gas smell, active flooding, etc.), which routes straight to
             the escalation node and bypasses ticket_creation entirely — so a ticket can never
             actually reach assign_vendor with urgency="EMERGENCY" in the current graph. Flagging
             this as an existing gap rather than silently working around it — see chat notes below.
  - Test 4: General issue -> no location match -> FALLBACK_POOL vendor -> human APPROVES -> ASSIGNED

Run with: python test_maintenance_stage4.py
"""

import asyncio
import sys
import os
import json
from dotenv import load_dotenv
import psycopg
from langgraph.types import Command

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage
from app.orchestrator.maintenance.graph import maintenance_graph
from app.orchestrator.maintenance.mcp_client import mcp_client

DATABASE_URL = os.getenv("DATABASE_URL")


# ── DB verification helpers ────────────────────────────────────────────

async def show_tickets(label: str, unit_id: str = None):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            query = (
                "SELECT ticket_id, unit_id, category, urgency, status, "
                "vendor_id, assignment_status FROM maintenance_tickets "
            )
            if unit_id:
                query += "WHERE unit_id = %s ORDER BY created_at DESC"
                await cur.execute(query, (unit_id,))
            else:
                query += "ORDER BY created_at DESC LIMIT 20"
                await cur.execute(query)
            rows = await cur.fetchall()
    print(f"\n  [DB CHECK — maintenance_tickets] {label}")
    if rows:
        print(f"  {'ticket_id':<15} {'unit_id':<8} {'category':<12} {'urgency':<10} {'status':<8} {'vendor_id':<10} assignment_status")
        print(f"  {'-'*90}")
        for r in rows:
            print(f"  {str(r[0]):<15} {str(r[1]):<8} {str(r[2]):<12} {str(r[3]):<10} {str(r[4]):<8} {str(r[5]):<10} {r[6]}")
    else:
        print("  (no rows)")


async def show_vendors(label: str):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT vendor_id, name, category, is_contracted, accepts_emergency, "
                "capacity, active_jobs FROM vendors ORDER BY vendor_id"
            )
            rows = await cur.fetchall()
    print(f"\n  [DB CHECK — vendors] {label}")
    print(f"  {'vendor_id':<10} {'name':<24} {'category':<12} {'contracted':<11} {'emergency':<10} active_jobs/capacity")
    print(f"  {'-'*90}")
    for r in rows:
        print(f"  {str(r[0]):<10} {str(r[1]):<24} {str(r[2]):<12} {str(r[3]):<11} {str(r[4]):<10} {r[6]}/{r[5]}")


async def show_assignment_attempts(label: str, limit: int = 15):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT ticket_id, strategy_used, result, reason, timestamp "
                "FROM assignment_attempts ORDER BY timestamp DESC LIMIT %s",
                (limit,),
            )
            rows = await cur.fetchall()
    print(f"\n  [DB CHECK — assignment_attempts] {label} (latest {limit})")
    if rows:
        for r in rows:
            print(f"  [{r[4]}] {r[0]} | {r[1]:<20} -> {r[2]:<12} | {r[3]}")
    else:
        print("  (no rows)")


async def reset_for_test():
    """Clear tickets/attempts/audit for a clean run, reset vendor active_jobs to seed baseline."""
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM assignment_attempts")
            await cur.execute("DELETE FROM ticket_status_log")
            await cur.execute("DELETE FROM maintenance_tickets")
            await cur.execute("DELETE FROM audit_logs")
            await cur.execute("""
                UPDATE vendors SET active_jobs = CASE vendor_id
                    WHEN 'V-100' THEN 1
                    WHEN 'V-101' THEN 0
                    WHEN 'V-102' THEN 0
                    WHEN 'V-103' THEN 2
                    WHEN 'V-104' THEN 2
                    WHEN 'V-105' THEN 0
                    ELSE active_jobs
                END
            """)
            # Note: V-104 (general, capacity 2) is deliberately reset to active_jobs=2 (fully booked)
            # so Test 4 below actually exercises the FALLBACK_POOL branch instead of matching
            # V-104 directly via LOCATION_BASED.
        await conn.commit()
    print("  [DB] Reset tickets/attempts/audit_logs. Vendor active_jobs reset to seed baseline.")


# ── Conversation runner with interrupt/resume handling ─────────────────

async def run_conversation_with_approval(test_name, thread_id, user_id, messages, approve_decision: str):
    """
    approve_decision: "yes" to approve the proposed vendor, "no" to reject.
    If the graph never hits human_approval (e.g. EXHAUSTED path skips it),
    approve_decision is simply unused.
    """
    print(f"\n{'='*75}")
    print(f"TEST: {test_name}")
    print(f"{'='*75}")
    config = {"configurable": {"thread_id": thread_id}}
    result = None

    for i, msg in enumerate(messages):
        print(f"\n--- Turn {i+1} ---")
        print(f"User: {msg}")
        input_state = {"messages": [HumanMessage(content=msg)], "user_id": user_id}
        result = await maintenance_graph.ainvoke(input_state, config)

        if isinstance(result, dict) and "__interrupt__" in result:
            interrupt_obj = result["__interrupt__"][0]
            payload = interrupt_obj.value
            print(f"\n  [HUMAN APPROVAL REQUIRED]")
            print(f"  Ticket:      {payload.get('ticket_id')}")
            print(f"  Unit:        {payload.get('unit_id')}")
            print(f"  Category:    {payload.get('category')}")
            print(f"  Description: {payload.get('description')}")
            print(f"  Urgency:     {payload.get('urgency')}")
            print(f"  Strategy:    {payload.get('strategy_used')}")
            vendor = payload.get("proposed_vendor", {})
            print(f"  Proposed vendor: {vendor.get('name')} ({vendor.get('vendor_id')}) — {vendor.get('phone')}")
            print(f"  >> Simulating human decision: {approve_decision.upper()}")

            result = await maintenance_graph.ainvoke(Command(resume=approve_decision), config)

        if isinstance(result, dict):
            print(f"\nAgent: {result.get('final_response')}")

    return result


# ── Main ─────────────────────────────────────────────────────────────

async def main():
    print("\n===== Stage 4 Integration Tests: Vendor Assignment + Human-in-the-Loop =====\n")

    await mcp_client.connect()
    await reset_for_test()
    await show_vendors("Baseline before tests")

    try:
        # ── TEST 1: Plumbing -> CONTRACTED vendor (V-100) -> APPROVE ──────
        await run_conversation_with_approval(
            test_name="Test 1 — Plumbing issue, contracted vendor match, human APPROVES",
            thread_id="s4_thread_1",
            user_id="+923001234567",
            messages=[
                "Hi, my bathroom sink is leaking. It's a plumbing issue, low urgency.",
                "Yes, you can enter. No pets."
            ],
            approve_decision="yes",
        )
        await show_tickets("After Test 1", unit_id="U-4B")

        # ── TEST 2: Electrical -> LOCATION_BASED (V-102) -> REJECT ────────
        await run_conversation_with_approval(
            test_name="Test 2 — Electrical issue, location-based match, human REJECTS",
            thread_id="s4_thread_2",
            user_id="tenant@example.com",
            messages=[
                "My outlet is sparking. Electrical issue, medium urgency.",
                "Yes, you can enter. No pets."
            ],
            approve_decision="no",
        )
        await show_tickets("After Test 2", unit_id="U-12")

        # ── TEST 3: Security issue -> zero vendors anywhere -> EXHAUSTED ────────
        await run_conversation_with_approval(
            test_name="Test 3 — Security issue, no vendor of this category anywhere, EXHAUSTED",
            thread_id="s4_thread_3",
            user_id="+923001234567",
            messages=[
                "My door lock is broken. Security issue, medium urgency.",
                "Yes, you can enter. No pets."
            ],
            approve_decision="yes",  # unused — EXHAUSTED path skips human_approval entirely
        )
        await show_tickets("After Test 3", unit_id="U-4B")

        # ── TEST 4: General issue -> FALLBACK_POOL (V-105) -> APPROVE ─────
        await run_conversation_with_approval(
            test_name="Test 4 — General issue, no local match, falls back to on-call pool",
            thread_id="s4_thread_4",
            user_id="tenant@example.com",
            messages=[
                "My cabinet door fell off, general repair needed, low urgency.",
                "Yes, you can enter. No pets."
            ],
            approve_decision="yes",
        )
        await show_tickets("After Test 4", unit_id="U-12")

        # ── Full picture ───────────────────────────────────────────────
        await show_assignment_attempts("All attempts across all tests")
        await show_vendors("After all tests (active_jobs should reflect ASSIGNED tickets)")

    finally:
        await mcp_client.disconnect()
        print("\n===== All Stage 4 tests complete. MCP client disconnected. =====\n")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
