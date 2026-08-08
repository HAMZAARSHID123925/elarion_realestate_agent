import asyncio
import sys
import os

# Add the root directory to sys.path so we can import the mcp_client
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core_workflows.maintenance.mcp_client import MaintenanceMCPClient

async def main():
    print("--- Starting Standalone MCP Client Test ---")
    client = MaintenanceMCPClient()
    
    try:
        # 1. Connect to the server
        print("\n[1] Connecting to MCP Server...")
        await client.connect()
        print("Connected successfully!")
        
        # 2. List tools
        print("\n[2] Listing available tools...")
        tools_response = await client.list_tools()
        for tool in tools_response.tools:
            print(f"  - {tool.name}: {tool.description}")
            
        # 3. Call lookup_property with a fake ID
        print("\n[3] Calling lookup_property with unit_id='U-12'...")
        result_valid = await client.call_tool("lookup_property", {"unit_id": "U-12"})
        print(f"Result: {result_valid}")
        
        # 4. Call lookup_property with an invalid ID
        print("\n[4] Calling lookup_property with unit_id='INVALID'...")
        result_invalid = await client.call_tool("lookup_property", {"unit_id": "INVALID"})
        print(f"Result: {result_invalid}")

    except Exception as e:
        print(f"Error during MCP interaction: {e}")
    finally:
        print("\n[5] Disconnecting...")
        await client.disconnect()
        print("Disconnected.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
