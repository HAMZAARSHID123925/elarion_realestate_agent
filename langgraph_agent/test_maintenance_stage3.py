import asyncio
import sys
import os
import json
from dotenv import load_dotenv
import psycopg

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage
from app.orchestrator.maintenance.graph import maintenance_graph
from app.orchestrator.maintenance.mcp_client import mcp_client

DATABASE_URL = os.getenv("DATABASE_URL")

# ── DB verification helpers ───────────────────────────────────────────

async def show_tickets(label: str, unit_id: str = None):
    """Print all tickets from Postgres (optionally filtered by unit)."""
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            if unit_id:
                await cur.execute(
                    "SELECT ticket_id, tenant_id, unit_id, category, urgency, status, created_at "
                    "FROM maintenance_tickets WHERE unit_id = %s ORDER BY created_at DESC",
                    (unit_id,),
                )
            else:
                await cur.execute(
                    "SELECT ticket_id, tenant_id, unit_id, category, urgency, status, created_at "
                    "FROM maintenance_tickets ORDER BY created_at DESC LIMIT 20"
                )
            rows = await cur.fetchall()
    print(f"\n  [DB CHECK — maintenance_tickets] {label}")
    if rows:
        print(f"  {'ticket_id':<15} {'tenant_id':<10} {'unit_id':<8} {'category':<14} {'urgency':<12} {'status':<8} created_at")
        print(f"  {'-'*90}")
        for r in rows:
            print(f"  {str(r[0]):<15} {str(r[1]):<10} {str(r[2]):<8} {str(r[3]):<14} {str(r[4]):<12} {str(r[5]):<8} {r[6]}")
    else:
        print("  (no rows)")

async def show_audit_logs(label: str, limit: int = 5):
    """Print the latest N audit log rows from Postgres."""
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT log_id, action, actor, details, timestamp "
                "FROM audit_logs ORDER BY timestamp DESC LIMIT %s",
                (limit,),
            )
            rows = await cur.fetchall()
    print(f"\n  [DB CHECK — audit_logs] {label} (latest {limit})")
    if rows:
        for r in rows:
            print(f"  [{r[4]}] log_id={r[0]} | {r[2]} | {r[1]}: {r[3]}")
    else:
        print("  (no rows)")

async def clear_tickets():
    """Clear all tickets and audit logs before each run for a clean state."""
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM assignment_attempts")
            await cur.execute("DELETE FROM ticket_status_log")
            await cur.execute("DELETE FROM maintenance_tickets")
            await cur.execute("DELETE FROM audit_logs")
        await conn.commit()
    print("  [DB] Cleared tickets, status_log, assignment_attempts, and audit_logs for fresh test run.")

# ── Conversation runner ───────────────────────────────────────────────

async def run_conversation(test_name, thread_id, user_id, messages):
    print(f"\n{'='*65}")
    print(f"TEST: {test_name}")
    print(f"{'='*65}")
    config = {"configurable": {"thread_id": thread_id}}
    for i, msg in enumerate(messages):
        print(f"\n--- Turn {i+1} ---")
        print(f"User: {msg}")
        input_state = {"messages": [HumanMessage(content=msg)], "user_id": user_id}
        try:
            result = await maintenance_graph.ainvoke(input_state, config)
            print(f"Agent: {result.get('final_response')}")
            print(f"  slots -> category={result.get('issue_category')} | urgency={result.get('urgency')} | "
                  f"pte={result.get('permission_to_enter')} | pets={result.get('pets_present')} | "
                  f"missing={result.get('missing_slots')}")
        except Exception as e:
            print(f"[GRAPH ERROR] {e}")

# ── Main ──────────────────────────────────────────────────────────────

async def main():
    print("\n===== Stage 3 Integration Tests: Real Postgres via MCP =====\n")

    # Single connect/disconnect for the whole test run
    await mcp_client.connect()

    # Clear DB for a clean run
    await clear_tickets()

    try:
        # ── TEST 1: Clean single-issue, all slots naturally provided ──
        await run_conversation(
            test_name="Test 1 — Clean single-issue, all slots provided",
            thread_id="s3_thread_1",
            user_id="+923001234567",
            messages=[
                "Hi, my bathroom sink is leaking. It's a plumbing issue, low urgency.",
                "Yes, you can enter. No pets."
            ]
        )
        await show_tickets("After Test 1", unit_id="U-4B")
        await show_audit_logs("After Test 1")

        # ── TEST 2: Missing mandatory field — graph should ask ─────────
        await run_conversation(
            test_name="Test 2 — Missing urgency, graph asks for it",
            thread_id="s3_thread_2",
            user_id="+923001234567",
            messages=[
                "My AC isn't working. HVAC issue. You can enter, no pets.",
                # Urgency deliberately omitted — agent should ask
                "It's medium urgency.",
            ]
        )
        await show_tickets("After Test 2", unit_id="U-4B")
        await show_audit_logs("After Test 2")

        # ── TEST 3: Emergency keyword → immediate escalation ──────────
        await run_conversation(
            test_name="Test 3 — Emergency keyword, instant escalation",
            thread_id="s3_thread_3",
            user_id="tenant@example.com",
            messages=[
                "Help! There is active flooding in the kitchen!"
            ]
        )
        await show_tickets("After Test 3 (no ticket — escalated)", unit_id="U-12")
        await show_audit_logs("After Test 3")

        # ── TEST 4: Duplicate ticket ────────────────────────────────
        # First create a plumbing ticket for U-4B (same category as test 1)
        print(f"\n{'='*65}")
        print("TEST: Test 4 — Duplicate ticket for same unit+category")
        print(f"{'='*65}")
        print("\nManually inserting a plumbing ticket for U-4B to simulate existing open ticket...")
        async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO maintenance_tickets
                       (ticket_id, tenant_id, property_id, unit_id, category, description,
                        urgency, permission_to_enter, pets_present, status, source_channel,
                        created_by, idempotency_key)
                       VALUES ('TKT-EXIST01','T-100','P-100','U-4B','plumbing',
                               'Pre-existing leak','low','yes','no','OPEN','voice','test',
                               'idem-pre-existing-key')
                    """
                )
            await conn.commit()
        print("Pre-existing open plumbing ticket inserted for U-4B.")

        dup_result = await mcp_client.call_tool("create_ticket", {
            "tenant_id": "T-100", "unit_id": "U-4B", "category": "plumbing",
            "description": "Another dripping pipe", "urgency": "low",
            "permission_to_enter": "yes", "pets_present": "no",
            "idempotency_key": "idem-dup-test-key-001",
        })
        print(f"\nDuplicate create_ticket response:\n  {dup_result}")
        await show_tickets("After Test 4 duplicate attempt", unit_id="U-4B")
        await show_audit_logs("After Test 4")

        # ── TEST 5: Unknown caller ─────────────────────────────────
        await run_conversation(
            test_name="Test 5 — Unknown caller, graceful fallback",
            thread_id="s3_thread_5",
            user_id="nobody@nowhere.com",
            messages=[
                "Hi, my door lock is broken. It's a security issue, high urgency.",
                "I'm Alex Park, unit 99.",
                "Yes, you can enter. No pets."
            ]
        )
        await show_tickets("After Test 5", unit_id="U-4B")
        await show_audit_logs("After Test 5")

        # ── IDEMPOTENCY VERIFICATION ───────────────────────────────
        print(f"\n{'='*65}")
        print("IDEMPOTENCY VERIFICATION")
        print(f"{'='*65}")
        # Get the ticket_id from Test 1 to replay with same idempotency key
        async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT ticket_id, idempotency_key FROM maintenance_tickets "
                    "WHERE tenant_id='T-100' AND category='plumbing' AND ticket_id != 'TKT-EXIST01' "
                    "ORDER BY created_at LIMIT 1"
                )
                row = await cur.fetchone()

        if row:
            original_id, idem_key = row
            print(f"\nOriginal ticket_id from Test 1: {original_id}")
            print(f"Replaying create_ticket with the exact same idempotency_key: {idem_key}")

            # Count tickets before replay
            async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT COUNT(*) FROM maintenance_tickets")
                    count_before = (await cur.fetchone())[0]

            replay_result = await mcp_client.call_tool("create_ticket", {
                "tenant_id": "T-100", "unit_id": "U-4B", "category": "plumbing",
                "description": "REPLAYED — should not create new row",
                "urgency": "low", "permission_to_enter": "yes", "pets_present": "no",
                "idempotency_key": idem_key,
            })
            replay_json = json.loads(replay_result)
            print(f"\nReplay response: {replay_result}")

            # Count tickets after replay
            async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT COUNT(*) FROM maintenance_tickets")
                    count_after = (await cur.fetchone())[0]

            print(f"\n  Ticket count BEFORE replay: {count_before}")
            print(f"  Ticket count AFTER  replay: {count_after}")
            returned_id = replay_json.get("ticket", {}).get("ticket_id")
            if returned_id == original_id and count_before == count_after:
                print(f"  [PASS] Same ticket_id ({returned_id}) returned. No new row created.")
            else:
                print(f"  [FAIL] Idempotency broken! returned={returned_id}, original={original_id}")
        else:
            print("  Could not find Test 1 ticket to verify idempotency.")

    finally:
        await mcp_client.disconnect()
        print("\n===== All Stage 3 tests complete. MCP client disconnected. =====\n")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
