import sys
import os
import json
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MaintenanceMCPClient:
    def __init__(self):
        self.session = None
        self._exit_stack = AsyncExitStack()
        
    async def connect(self):
        """Connects to the local MCP server over stdio."""
        if self.session:
            return # already connected
            
        # The MCP server is located at the root of langgraph_agent
        server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../mcp_server.py"))
        
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[server_path]
        )
        
        stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
        self.read, self.write = stdio_transport
        self.session = await self._exit_stack.enter_async_context(ClientSession(self.read, self.write))
        
        await self.session.initialize()
        print("[MCP Client] Connected to MaintenanceServer over stdio.")

    async def list_tools(self):
        """List all available tools from the MCP server."""
        if not self.session:
            raise RuntimeError("MCP Client not connected. Call connect() first.")
        return await self.session.list_tools()

    async def call_tool(self, name: str, arguments: dict):
        """Execute a tool on the MCP server."""
        if not self.session:
            raise RuntimeError("MCP Client not connected. Call connect() first.")
        
        result = await self.session.call_tool(name, arguments=arguments)
        
        # Tools typically return a list of text content blocks
        if result and result.content:
            # Assuming the primary output is the text of the first content block
            return result.content[0].text
        return None

    async def disconnect(self):
        """Close the stdio transport and session."""
        await self._exit_stack.aclose()
        self.session = None

# Global instance for the LangGraph nodes to use
mcp_client = MaintenanceMCPClient()
