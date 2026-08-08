import warnings
import logging
warnings.filterwarnings("ignore")
# LangGraph emits checkpoint deserialization notices via the logging module,
# not via warnings -- silence them here before any import runs.
logging.getLogger("langgraph").setLevel(logging.ERROR)
logging.getLogger("langgraph_core").setLevel(logging.ERROR)

import asyncio
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Add the project root to sys.path so 'mcp_servers' can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.pipeline import invoke_pipeline, resume_pipeline
from app.core_workflows.maintenance.mcp_client import mcp_client as maintenance_mcp
from app.core_workflows.faq.mcp_client import property_mcp_client as faq_mcp

async def main():
    print("Starting up and connecting to tools... Please wait.")
    try:
        await maintenance_mcp.connect()
        await faq_mcp.connect()
    except Exception as e:
        print(f"Warning: Failed to connect to one or more MCP servers: {e}")
        print("Workflows that require those MCP tools may fail.")

    print("Welcome to Elarion! Type 'exit' or 'quit' to stop.")
    user_id = "terminal_user"
    channel = "terminal"
    
    try:
        while True:
            try:
                user_input = input("\nYou: ")
                if user_input.strip().lower() in ['exit', 'quit']:
                    break
                if not user_input.strip():
                    continue
                    
                result, config = await invoke_pipeline(
                    channel=channel, 
                    user_id=user_id, 
                    raw_text=user_input
                )
                
                while "__interrupt__" in result:
                    interrupt_payloads = result["__interrupt__"]
                    
                    # Depending on LangGraph version, it may be a single payload or a tuple of Interrupt objects
                    if isinstance(interrupt_payloads, tuple) and len(interrupt_payloads) > 0:
                        payload = interrupt_payloads[0].value if hasattr(interrupt_payloads[0], 'value') else interrupt_payloads[0]
                    else:
                        payload = interrupt_payloads
                    
                    print(f"\n[SYSTEM PAUSED] Human approval requested!")
                    try:
                        print(f"Payload: {json.dumps(payload, indent=2)}")
                    except Exception:
                        print(f"Payload: {payload}")
                    
                    decision = input("Approve? (yes/no): ").strip().lower()
                    
                    print(f"Resuming with value: {decision}...")
                    result, config = await resume_pipeline(config, decision)
                    
                if "final_response" in result:
                    print(f"Elarion: {result['final_response']}")
                else:
                    print(f"Elarion [raw result]: {result}")
                    
            except (KeyboardInterrupt, asyncio.CancelledError):
                print("\n[Request cancelled by user. Type 'exit' to stop.]")
                continue
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
    finally:
        await maintenance_mcp.disconnect()
        await faq_mcp.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
