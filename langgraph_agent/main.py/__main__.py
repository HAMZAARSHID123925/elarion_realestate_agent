import sys
import os

# Ensure the parent directory is in the path so we can import 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from app.graph import graph

def main():
    # Load API key from .env (the one in the root or main.py folder)
    # We will try the root first, then fall back
    root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    if os.path.exists(root_env):
        load_dotenv(root_env)
    else:
        load_dotenv()
        
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found. Please set it in your .env file.")
        sys.exit(1)
        
    print("Welcome to the Real Estate Voice Agent MVP!")
    print("Type 'exit' or 'quit' to stop the conversation.\n")
    
    # Create conversation_id
    conversation_id = str(uuid.uuid4())
    
    # Initialize state
    state = {
        "conversation_id": conversation_id,
        "user_name": None,
        "user_city": None,
        "user_goal": None,
        "messages": [],
        "conversation_summary": None,
        "is_conversation_complete": False
    }
    
    # Use while loop
    while not state.get("is_conversation_complete", False):
        try:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting conversation.")
                break
                
            # Append to messages
            state["messages"].append(HumanMessage(content=user_input))
            
            # graph.invoke()
            state = graph.invoke(state)
            
            # Print latest assistant response
            if state.get("messages"):
                latest_message = state["messages"][-1]
                if latest_message.type == "ai":
                    print(f"Assistant: {latest_message.content}")
                    
        except KeyboardInterrupt:
            print("\nExiting conversation.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    # When complete:
    if state.get("is_conversation_complete", False):
        print("\nConversation Summary:")
        print(state.get("conversation_summary", "No summary available."))
        
    print("\nGoodbye!")

if __name__ == "__main__":
    main()
