import asyncio
import sys
import os
from dotenv import load_dotenv
import logging
from unittest import mock

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator.schemas import UnifiedRequest
from app.orchestrator.graph import orchestrator_graph
from app.orchestrator.nodes import identification_node
from app.core_workflows.maintenance.mcp_client import mcp_client

# Setup simple logging to see what happens
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def test_identification_node():
    """
    Isolated unit test for identification_node (item 5.9 fix), run WITHOUT a live
    DB/MCP connection -- mcp_client.call_tool is mocked with unittest.mock so this
    is a real, individually-runnable test of the identification logic itself, not
    an end-to-end integration test. Uses plain `assert` (pass/fail), unlike the
    rest of this file which only prints output for a human to eyeball.

    Covers the exact question this fix needs to answer correctly:
      1. A phone/email that IS a real row in tenants -> status 'known', role 'tenant',
         real tenant_id/property_id from the DB row (not a hardcoded value).
      2. A phone/email that is NOT in tenants -> status 'unknown', role 'guest'.
         Guest is a LABEL only -- see rules_engine_node, which computes `role` but
         never branches on it, so this does not deny or degrade service; it only
         records whether the caller matched a real tenant record.
      3. The MCP client not being connected / raising -> also falls back to guest
         instead of raising, so a DB hiccup can never crash the pipeline.
    """
    print("\n--- Testing identification_node (isolated, mocked mcp_client) ---\n")

    # Case 1: real tenant match
    fake_found_json = '{"tenant_id": "TEN-001", "name": "Hamza", "unit_id": "U-12", "property_id": "PROP-01"}'
    with mock.patch.object(mcp_client, "call_tool", new=mock.AsyncMock(return_value=fake_found_json)):
        state = {"request": UnifiedRequest(channel="whatsapp", user_id="+923330533729", raw_text="hi")}
        result = await identification_node(state)
        profile = result["user_profile"]
        assert profile["status"] == "known", f"expected known, got {profile['status']}"
        assert profile["role"] == "tenant", f"expected tenant, got {profile['role']}"
        assert profile["user_id"] == "TEN-001", f"expected real tenant_id TEN-001, got {profile['user_id']}"
        assert profile["property_id"] == "PROP-01"
        print(f"[PASS] Known tenant resolved correctly: {profile}")

    # Case 2: no matching row -> guest (not a rejection, just an accurate label)
    fake_not_found_json = '{"error": "Tenant not found"}'
    with mock.patch.object(mcp_client, "call_tool", new=mock.AsyncMock(return_value=fake_not_found_json)):
        state = {"request": UnifiedRequest(channel="whatsapp", user_id="+92-random-caller", raw_text="hi")}
        result = await identification_node(state)
        profile = result["user_profile"]
        assert profile["status"] == "unknown"
        assert profile["role"] == "guest"
        assert profile["user_id"] == "+92-random-caller"  # unresolved caller ID is preserved, not dropped
        print(f"[PASS] Unmatched caller correctly labeled guest (not blocked): {profile}")

    # Case 3: MCP client errors out (e.g. not connected yet) -> fail closed, no crash
    with mock.patch.object(mcp_client, "call_tool", new=mock.AsyncMock(side_effect=RuntimeError("MCP Client not connected"))):
        state = {"request": UnifiedRequest(channel="whatsapp", user_id="+923001112222", raw_text="hi")}
        result = await identification_node(state)  # must NOT raise
        profile = result["user_profile"]
        assert profile["status"] == "unknown"
        assert profile["role"] == "guest"
        print(f"[PASS] MCP/DB error failed closed to guest instead of crashing: {profile}")

    print("\n--- identification_node: all 3 cases passed ---\n")

async def test_orchestrator():
    print("\n--- Starting Layer 2 Orchestrator Production Tests ---\n")
    
    test_cases = [
        {
            "name": "WhatsApp Maintenance (High Urgency)",
            "request": UnifiedRequest(
                channel="whatsapp",
                user_id="+923001234567",
                raw_text="The main pipe burst and my kitchen is flooding right now! Please send someone immediately!"
            )
        },
        {
            "name": "Email Leasing (Low Urgency)",
            "request": UnifiedRequest(
                channel="email",
                user_id="tenant@example.com",
                raw_text="Hello, I would like to know the process for renewing my lease next month. Thanks."
            )
        },
        {
            "name": "VAPI Property Search",
            "request": UnifiedRequest(
                channel="vapi",
                user_id="unknown_caller",
                raw_text="I am looking for a 3 bedroom apartment in Lahore under 200 lakhs."
            )
        },
        # --- EDGE CASES ---
        {
            "name": "EDGE CASE: Unknown Caller (Fail-Closed Test)",
            "request": UnifiedRequest(
                channel="vapi",
                user_id="+92-unknown-number",
                raw_text="hi"
            )
        },
        {
            "name": "EDGE CASE: Vague Problem (Needs More Info Test)",
            "request": UnifiedRequest(
                channel="whatsapp",
                user_id="+92xxxx",
                raw_text="there's a problem"
            )
        },
        {
            "name": "EDGE CASE: Extreme Urgency Wording",
            "request": UnifiedRequest(
                channel="email",
                user_id="unknown@email.com",
                raw_text="fire in the building!!!"
            )
        },
        {
            "name": "EDGE CASE: Empty Transcript",
            "request": UnifiedRequest(
                channel="vapi",
                user_id="+92xxxx",
                raw_text=""
            )
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test['name']} ---")
        
        # Initialize state
        input_state = {
            "request": test["request"]
        }
        
        try:
            # Use ainvoke for asynchronous execution (Fixes concurrency blocker)
            result_state = await orchestrator_graph.ainvoke(input_state)
            
            # Print the final Layer 2 Output (The UnifiedResponse)
            final_response = result_state.get("response")
            
            if final_response:
                print(f"[SUCCESS] Orchestrator Output:")
                print(f"  Intent:   {final_response.intent}")
                print(f"  Urgency:  {final_response.urgency}")
                print(f"  Entities: {final_response.extracted_entities}")
                print(f"  Action:   {final_response.action_taken}")
                print(f"  Reply:    {final_response.response_message}")
            else:
                print("[ERROR] Failed to generate a response.")
        except Exception as e:
            print(f"[CRITICAL FAILURE] Graph execution crashed: {e}")

if __name__ == "__main__":
    # Workaround for Windows asyncio bug if needed, though asyncio.run is usually fine for this
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def _run_all():
        await test_identification_node()   # isolated, no live DB/LLM needed
        await test_orchestrator()          # full graph, needs live DB + Groq key

    asyncio.run(_run_all())
