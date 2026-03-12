import os
import requests
import asyncio
from typing import Union, List, Any
from google.adk.agents.llm_agent import Agent
from mcp import ClientSession
from mcp.client.sse import sse_client
#from google.adk.tools.openapi_tool import OpenAPIToolset
#from google.adk.tools.openapi_tool.auth.auth_helpers import token_to_scheme_credential

# 1. Konfiguration des MCP-Servers
# Wichtig: Innerhalb von Docker nutzen wir den Service-Namen 'mcp' aus der docker-compose.yml
MCP_SERVER_URL = "http://fma:8002/mcp/sse"#"http://idea-agent-mcp:8001/sse"

# 2. Tools
async def explore_mcp_endpoint():
    """
    Diese Funktion verbindet sich mit dem MCP-Server und holt die verfügbaren Prompts/Tools.
    """
    async with sse_client(MCP_SERVER_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            
            await session.initialize()

            prompt_result = await session.list_prompts()
            tool_result = await session.list_tools()
            
            return {
                "prompts": prompt_result.prompts, 
                "tools": tool_result.tools
            }

async def read_graph(query: str) -> str:
    """
    Führt eine Cypher-Query in der Neo4j-Datenbank aus. Beachte, dass der Graph read-only ist.
    """
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("read_graph", arguments={"query": query})
            return result.content[0].text

async def get_unit_by_id(unit_id: Union[int, str]) -> Any:
    """
    Ruft den tiefen Kontext für eine oder mehrere Units über den MCP-Server ab.
    Akzeptiert einzelne Unit-IDs (Int/String) oder Listen davon.
    """

    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_unit_by_id", arguments={"id": unit_id})
            return result.content[0].text

# 3. ADK Agent Definition
# Wir erstellen einen Agenten, der später die MCP-Tools nutzen soll.
root_agent = Agent(
    model="gemini-2.5-flash",
    name="Curator",
    description="An Expert Agent for Reasoning based on GraphRAG.",
    instruction=(
        "Du bist ein Agent, der via MCP mit einer Neo4j-Instanz verbunden ist."
    ),
    tools=[explore_mcp_endpoint, read_graph, get_unit_by_id]
)

if __name__ == "__main__":
    # Dieser Teil wird von 'adk web' übernommen, 
    # kann aber für lokales Debugging genutzt werden.
    pass

