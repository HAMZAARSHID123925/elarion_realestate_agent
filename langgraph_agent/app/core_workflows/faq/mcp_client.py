"""
PropertySearchMCPClient -- connects to mcp_servers/property_search/server.py over stdio.

Same pattern as maintenance/mcp_client.py, pointed at the existing property
search server instead of the maintenance server. Reuses the already-built
search_properties / get_property_details / get_available_cities tools --
this workflow does not need its own MCP server.

Note on the design doc's request schema (section 5.1): the current
search_properties tool takes (location, property_type, budget) as a single
budget string. It does not yet support bedrooms, budget_min/budget_max as
separate fields, or availability_only/session_id. This client calls the tool
as it exists today; extending the MCP server to match the full section 5.1
schema is a follow-up, not a blocker for v1 (see summary report).
"""
import sys
import os
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class PropertySearchMCPClient:
    def __init__(self):
        self.session = None
        self._exit_stack = AsyncExitStack()

    async def connect(self):
        if self.session:
            return  # already connected

        # mcp_servers/property_search/server.py lives at the repo root, four
        # levels up from this file (faq/ -> orchestrator/ -> app/ -> langgraph_agent/ -> root)
        repo_root = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "..",
            )
        )
        server_path = os.path.join(repo_root, "mcp_servers", "property_search", "server.py")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = repo_root

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[server_path],
            env=env,
        )

        stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
        self.read, self.write = stdio_transport
        self.session = await self._exit_stack.enter_async_context(ClientSession(self.read, self.write))

        await self.session.initialize()
        print("[MCP Client] Connected to PropertySearchServer over stdio.")

    async def call_tool(self, name: str, arguments: dict):
        if not self.session:
            raise RuntimeError("MCP Client not connected. Call connect() first.")

        result = await self.session.call_tool(name, arguments=arguments)

        if result and result.content:
            return result.content[0].text
        return None

    async def disconnect(self):
        await self._exit_stack.aclose()
        self.session = None


# Global instance for the FAQ nodes to use, same convention as maintenance
property_mcp_client = PropertySearchMCPClient()
