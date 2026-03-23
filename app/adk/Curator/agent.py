import os
import requests
import asyncio
from typing import Optional, Dict, Union, List, Any
from google.adk.agents.llm_agent import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from mcp import ClientSession
from mcp.client.sse import sse_client
import base64

MCP_SERVER_URL = "http://fma:8001/mcp/sse"

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

async def get_onboarding_prompt(args: Optional[Dict[str, Any]] = None) -> str:
    """
    Ruft den Onboarding-Prompt vom MCP-Server ab.
    Akzeptiert optional Argumente, falls der Prompt in Zukunft welche benötigt.
    """
    prompt_args = args if args is not None else {}

    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Hier nutzen wir get_prompt statt call_tool
            result = await session.get_prompt("onboarding_briefing", arguments=prompt_args)
            
            # Bei Prompts steckt der Text in den 'messages' (meist als 'user' role)
            # Wir greifen auf die erste Nachricht zu und extrahieren den Text
            if result.messages and hasattr(result.messages[0].content, 'text'):
                return result.messages[0].content.text
            
            # Fallback, falls das SDK die Struktur leicht anders auflöst
            return str(result.messages)

async def read_graph(query: str) -> str:
    """
    Führt eine Cypher-Query in der Neo4j-Datenbank aus. Beachte, dass der Graph read-only ist.
    """
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("read_graph", arguments={"query": query})
            return result.content[0].text

async def get_unit_by_id(unit_id: int) -> Any:
    """
    Ruft den tiefen Kontext für eine oder mehrere Units über den MCP-Server ab.
    Akzeptiert einzelne Unit-IDs (Int) oder Listen davon.
    """

    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_unit_by_id", arguments={"id": unit_id})
            return result.content[0].text

async def get_similar_units_by_asset_id(asset_id: str) -> str:
    """
    Ruft den tiefen epistemischen Kontext für ein zuvor auf dem Server bereitgestelltes Bild ab.
    Erwartet die eindeutige Asset-ID (UUID).
    """
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_similar_units_by_asset_id", arguments={"asset_id": asset_id})
            return result.content[0].text

async def get_similar_units_by_image_url(image_url: str) -> str:
    """
    Ruft den tiefen epistemischen Kontext für ein zuvor auf dem Server bereitgestelltes Bild ab.
    Erwartet die eindeutige Asset-ID (UUID).
    """
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_similar_units_by_image_url", arguments={"image_url": image_url})
            return result.content[0].text

async def get_similar_units_by_image() -> str:
    """
    Ruft den tiefen epistemischen Kontext für ein bereitgestelltes Bild ab.
    """
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_similar_units_by_image")
            return result.content[0].text

# 3. ADK Agent Definition
# Wir erstellen einen Agenten, der später die MCP-Tools nutzen soll.
root_agent = Agent(
    model="gemini-3.1-flash-lite-preview", # gemini-2.5-flash
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048  # Optional: Legt das Limit für die Denk-Tokens fest
        )
    ),
    name="Curator",
    description="An Expert Agent for Reasoning based on GraphRAG.",
    instruction=(
        "You are a highly specialized, multimodal Expert Agent AI system for visual and epistemic analysis."
        "\nIMPORTANT: ALWAYS call the initial onboarding with the tool `get_onboarding_prompt` at the beginning of a session. It will assist you during the following conversation."
        #"\nIMPORTANT: ALWAYS communicate in English with the user"
        "\nBe helpful: as an expert, you must not judge lightly; instead, you must carefully weigh your answers. You are helpful when you enlighten the user about all uncertainties and ambivalences and exercise restraint."
        "\nYou ARE capable of seeing and visually analyzing images directly. NEVER deny your ability to analyze images."
        "\nYou can access a Neo4j Knowledge Graph via MCP."
        "\nMANDATORY procedure when the user provides an image for analysis:"
        "\n* If not already done at the beginning of the session, call the tool `get_onboarding_prompt`"
        "\n* First, use the tool 'get_similar_units_by_image': The endpoint will return image descriptions for *visually similar* images (if available)"
        "\n* Conduct a morphological analysis; avoid speculative semantic interpretations and remain on the visual level"
        "\n* Use the retrieved descriptions to refine your analysis"
        "\n* Process the graph-based description into natural language for the user to create a pleasant reading flow. Align your style with the terminology of a corresponding academic expert"
        "\n* Note that the graph is still very limited and the embedding model is not fine-tuned (even a very high similarity score > 0.95 can be deceptive)"
        "\n* Always weight your own morphological analysis higher than the comparative material and carefully check for potential parallels."
        "\n* Point out to the user that visual similarity is not identical to semantic similarity if you have doubts about the fit."
        "\n* Before answering double check your answer whether it fits the graph data. Be pedantic!"
    ),
    tools=[get_onboarding_prompt, explore_mcp_endpoint, read_graph, get_unit_by_id, get_similar_units_by_image]
)

if __name__ == "__main__":
    # Dieser Teil wird von 'adk web' übernommen, 
    # kann aber für lokales Debugging genutzt werden.
    pass

