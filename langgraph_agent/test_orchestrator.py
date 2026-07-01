import asyncio
import sys
import os
from dotenv import load_dotenv
import logging

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator.schemas import UnifiedRequest
from app.orchestrator.graph import orchestrator_graph

# Setup simple logging to see what happens
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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
    asyncio.run(test_orchestrator())
