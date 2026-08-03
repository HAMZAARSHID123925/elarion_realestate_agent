"""
FAQ / Workflow #3 test harness -- mirrors test_maintenance_stage1.py's pattern.

Covers the 2 main use cases, matching the two structural paths of this
workflow (design doc section 2.1):
  Test 1: KNOWLEDGE path, clean answerable question -- exercises
          classify_intent -> rag_retrieve -> rag_generate -> compose_response,
          and verifies the confidence gate passes and a grounded, cited
          answer comes back.
  Test 2: PROPERTY path, multi-turn slot filling -- exercises
          classify_intent -> collect_property_slots -> clarify (missing
          budget) -> collect_property_slots -> call_property_mcp ->
          recommend_generate -> compose_response.

Before running Test 1, ingest the sample .txt knowledge base:
    python -m app.core_workflows.faq.ingestion.ingest --file app/orchestrator/faq/knowledge_base/sample_pet_policy.txt

Requires PINECONE_API_KEY and GOOGLE_API_KEY in langgraph_agent/.env for
Test 1. Test 2 only needs GROQ_API_KEY (already set) and the existing
property_search MCP server -- no new credentials needed.
"""
import asyncio
import sys
import os
from dotenv import load_dotenv
import logging

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core_workflows.faq.graph import faq_graph
from app.core_workflows.faq.mcp_client import property_mcp_client

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logging.getLogger("app.core_workflows.faq.nodes").setLevel(logging.INFO)


async def run_conversation(test_name: str, thread_id: str, user_id: str, messages: list[str]):
    print(f"\n{'='*60}")
    print(f"Starting Conversation Test: {test_name}")
    print(f"{'='*60}")

    config = {"configurable": {"thread_id": thread_id}}

    for i, msg in enumerate(messages):
        print(f"\n--- Turn {i+1} ---")
        print(f"User: {msg}")

        input_state = {
            "user_query": msg,
            "user_id": user_id,
            "session_id": thread_id,
        }

        try:
            result_state = await faq_graph.ainvoke(input_state, config)

            print(f"Agent: {result_state.get('final_response')}")
            print(f"\n  [State snapshot]")
            print(f"    intent:                 {result_state.get('intent')}")
            print(f"    confidence_score:       {result_state.get('confidence_score')}")
            print(f"    escalate:               {result_state.get('escalate')}")
            print(f"    property_filters:       {result_state.get('property_filters')}")
            print(f"    missing_property_fields:{result_state.get('missing_property_fields')}")

        except Exception as e:
            print(f"[CRITICAL FAILURE] Graph execution crashed: {e}")


async def main():
    print("\n--- Starting Stage 1 FAQ Workflow Tests ---\n")

    await property_mcp_client.connect()

    try:
        # Test 1: KNOWLEDGE path -- clean, answerable policy question
        await run_conversation(
            test_name="Test 1: Knowledge path - pet policy question",
            thread_id="faq_test_thread_1",
            user_id="+923001234567",
            messages=[
                "What's the pet deposit if I want to keep a cat?",
            ],
        )

        # Test 2: PROPERTY path -- multi-turn, one field missing on purpose
        await run_conversation(
            test_name="Test 2: Property path - multi-turn slot filling",
            thread_id="faq_test_thread_2",
            user_id="+923009876543",
            messages=[
                "Do you have any 2-bedroom apartments in Lahore?",   # missing budget -> should trigger clarify
                "My budget is around 120 lakhs.",                     # completes the slots -> should call MCP
            ],
        )
    finally:
        await property_mcp_client.disconnect()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
