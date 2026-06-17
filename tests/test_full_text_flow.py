"""
End-to-end text test: simulates a full real estate conversation
Run from repo root: python tests/test_full_text_flow.py
"""
import sys, os
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("langgraph_agent"))

from dotenv import load_dotenv
load_dotenv(".env")

from langchain_core.messages import HumanMessage
from app.graph import graph

def run_test():
    print("\n" + "="*50)
    print("ELARION - Text Flow Test (No Voice)")
    print("="*50 + "\n")

    state = {
        "conversation_id": "test-001",
        "user_name": None,
        "location": None,
        "user_goal": None,
        "budget": None,
        "property_type": None,
        "messages": [],
        "conversation_summary": None,
        "is_conversation_complete": False,
        "next_step": None,
        "property_search_result": None
    }

    # Simulate conversation turns
    turns = [
        "Hi I am Usman",
        "I want a house",
        "In karachi",
        "Budget is 200 lakhs",
    ]

    for user_msg in turns:
        print(f"User: {user_msg}")
        state["messages"].append(HumanMessage(content=user_msg))
        state = graph.invoke(state)

        # Print agent reply
        msgs = state.get("messages", [])
        if msgs and msgs[-1].type == "ai":
            print(f"Agent: {msgs[-1].content}")

        # Check if search happened
        if state.get("property_search_result"):
            result = state["property_search_result"]
            print(f"\n{'='*40}")
            print(f"MCP RESULT: {result['status']}")
            print(f"Found: {result.get('count', 0)} properties")
            for p in result.get("properties", []):
                print(f"  -> {p['title']} | {p['price']} lakhs | {p['city']}")
            print(f"{'='*40}\n")
            break

        if state.get("is_conversation_complete"):
            break

    print("\n[SUCCESS] Test complete!")

if __name__ == "__main__":
    run_test()