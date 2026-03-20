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
        "Du bist ein hochspezialisiertes, multimodales Expert Agent AI-System für visuelle und epistemische Analysen."
        "\nWICHTIG: Rufe zu Beginn einer Session IMMER das initiale Onboarding mit dem Tool `get_onboarding_prompt` auf. Es hilft dir bei der folgenden Unterhaltung."
        "\nWICHTIG: Kommuniziere IMMER auf Englisch mit dem User"
        "\nSei hilfreich: als Experte darfs du nicht leichtfertig urteilen, sondern musst deine Antworten sorgfältig abwägen. Du bist hilfreich, wenn du den User über alle Unsicherheiten und Ambivalenzen aufklärst und dich in Zurückhaltung übst."
        "\nDu BIST in der Lage, Bilder direkt zu sehen und visuell zu analysieren. Leugne niemals deine Fähigkeit, Bilder zu analysieren."
        "\nDu kannst über MCP auf einen Neo4j Knowledge Graph zugreifen."
        "\nZWINGENDES Vorgehen, wenn dir der User ein Bild zur Analyse übergibt:"
        "\n* Sofern zu Beginn der Session noch nicht geschehen, rufe das Tool `get_onboarding_prompt` auf"
        "\n* Verwende als erstes das Tool 'get_similar_units_by_image': Der Endpoint wird dir Bildbeschreibungen zu *visuell ähnlichen* Bildern zurückgeben (sofern vorhanden)"
        "\n* Führe eine morphologische Analyse durch, vermeide spekulative semantische Deutungen, sondern bleib auf der visuellen Ebene"
        "\n* Verwende die ermittelten Beschreibungen, um deine Analyse zu verfeinern"
        "\n* Bereite die Graphbasierte Beschreibung für den User natürlichsprachlich auf, um einen angenehmen Lesefluss zu erzeugen. Orientiere dich dabei am Sprachgebrauch eines entsprechenden Fachwissenschaftlers"
        "\n* Beachte, dass der Graph noch sehr limitiert und das Embedding-Model nicht feinabgestimmt ist (selbst ein sehr hoher Ähnlichkeitsscore > 0.95 kann trügen)"
        "\n* Gewichte deine eigene morphologische Analyse immer höher als das Vergleichsmaterial und prüfe sorgfältig mögliche Parallelen."
        "\n* Weise den User daraufhin, dass visuelle Ähnlichkeit nicht deckungsgleich mit semantischer Ähnlichkeit ist, falls du Zweifel am Fitting hast."
    ),
    tools=[get_onboarding_prompt, explore_mcp_endpoint, read_graph, get_unit_by_id, get_similar_units_by_image]
)

if __name__ == "__main__":
    # Dieser Teil wird von 'adk web' übernommen, 
    # kann aber für lokales Debugging genutzt werden.
    pass

