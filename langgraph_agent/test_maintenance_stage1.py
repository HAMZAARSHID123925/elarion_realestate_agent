import asyncio
import sys
import os
from dotenv import load_dotenv
import logging
from langchain_core.messages import HumanMessage

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core_workflows.maintenance.graph import maintenance_graph

# Setup simple logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
# Optional: Set app.maintenance.nodes to INFO to see our manual logs
logging.getLogger("app.maintenance.nodes").setLevel(logging.INFO)

async def run_conversation(test_name: str, thread_id: str, user_id: str, messages: list[str]):
    print(f"\n{'='*60}")
    print(f"Starting Conversation Test: {test_name}")
    print(f"{'='*60}")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    for i, msg in enumerate(messages):
        print(f"\n--- Turn {i+1} ---")
        print(f"User: {msg}")
        
        input_state = {
            "messages": [HumanMessage(content=msg)],
            "user_id": user_id
        }
        
        try:
            result_state = await maintenance_graph.ainvoke(input_state, config)
            
            final_response = result_state.get("final_response")
            
            print(f"Agent: {final_response}")
            print(f"\n  [Current Slots State]")
            print(f"    tenant_identity:     {result_state.get('tenant_identity')}")
            print(f"    property_unit:       {result_state.get('property_unit')}")
            print(f"    issue_category:      {result_state.get('issue_category')}")
            print(f"    issue_description:   {result_state.get('issue_description')}")
            print(f"    urgency:             {result_state.get('urgency')}")
            print(f"    permission_to_enter: {result_state.get('permission_to_enter')}")
            print(f"    pets_present:        {result_state.get('pets_present')}")
            print(f"    missing_slots:       {result_state.get('missing_slots')}")
            
            if "ticket_payload" in result_state and result_state["ticket_payload"]:
                print(f"    [TICKET CREATED] Payload: {result_state['ticket_payload']}")
            if "escalation_record" in result_state and result_state["escalation_record"]:
                print(f"    [ESCALATED] Record: {result_state['escalation_record']}")
                
        except Exception as e:
            print(f"[CRITICAL FAILURE] Graph execution crashed: {e}")

from app.core_workflows.maintenance.mcp_client import mcp_client

async def main():
    print("\n--- Starting Stage 1 Maintenance Workflow Tests ---\n")
    
    # 1. Connect the MCP client at the start of the entire test run
    await mcp_client.connect()
    
    try:
        # Test 1: Happy path with a known user and multiple turns
        await run_conversation(
            test_name="Test 1: Known User, Multi-turn plumbing issue",
            thread_id="test_thread_1",
            user_id="+923001234567",
            messages=[
                "Hi, I have a problem in my bathroom.",
                "The sink is leaking a little bit. It's a plumbing issue.",
                "It's not very urgent, just low urgency. Yes, you can enter, and I have no pets."
            ]
        )
        
        # Test 2: Unknown user, explicit slot correction
        await run_conversation(
            test_name="Test 2: Unknown User, Explicit Correction",
            thread_id="test_thread_2",
            user_id="unknown",
            messages=[
                "My oven is broken. I think it's an electrical issue.",
                "I'm John Smith, unit 101. Wait, actually I meant appliance issue, not electrical. The urgency is medium.",
                "No, you can't enter without me, and I have a dog (so yes to pets)."
            ]
        )
        
        # Test 3: Emergency Hardcoded Keyword Override
        await run_conversation(
            test_name="Test 3: Emergency Override",
            thread_id="test_thread_3",
            user_id="tenant@example.com",
            messages=[
                "Help, there is active flooding in the kitchen!",
                "It's obviously plumbing, high urgency! I am John Doe in House 12. Enter anytime, no pets."
            ]
        )
    finally:
        # 2. Cleanly disconnect at the end of the script
        await mcp_client.disconnect()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
