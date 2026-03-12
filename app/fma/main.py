import os
import asyncio
from contextlib import asynccontextmanager
from typing import Union, List, Annotated
from fastapi import FastAPI, Response, Request, HTTPException, Depends, Query, HTTPException
from mcp.server.sse import SseServerTransport

# WICHTIG: Hier importieren wir die Logik
from .lib.mcp.mcp_server import mcp_server
from .lib.db.neo4j import db, run_statement

# Der SSE-Transport braucht den Pfad zum Nachrichten-Endpunkt
sse = SseServerTransport("/mcp/messages")

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.connect() # Neo4j Start
    yield
    await db.close() # Neo4j Stop

# Das ist die FastAPI-App
app = FastAPI(title="GraphRAG API", lifespan=lifespan)

# --- MCP ---
async def mcp_asgi_app(scope, receive, send):
    if scope["type"] != "http":
        return

    # Wir säubern den Pfad (keine Slashes am Ende)
    path = scope.get("path", "").rstrip("/")
    
    # Debug-Print bleibt drin, falls wir nochmal schauen müssen
    #print(f"DEBUG: MCP-Anfrage auf Pfad: '{path}'")

    # Suffix-Matching: Wir prüfen, womit der Pfad endet
    if path.endswith("/sse") or path == "sse":
        async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options()
            )
    elif path.endswith("/messages") or path == "messages":
        await sse.handle_post_message(scope, receive, send)
    else:
        # 404 Fallback
        await send({
            "type": "http.response.start",
            "status": 404,
            "headers": [(b"content-type", b"text/plain")],
        })
        await send({"type": "http.response.body", "body": b"MCP Path Not Found"})

# Mounten: Alles unter /mcp geht an unsere Bridge
app.mount("/mcp", mcp_asgi_app)

# --- REST ---
@app.get("/")
async def root():
    return {"status": "online", "modes": ["REST", "MCP-SSE"]}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/graph/schema")
async def get_graph_schema():
    """
    Gibt eine Übersicht über alle Labels, Relationships 
    und deren Properties im Graphen zurück.
    """
    try:
        # 1. Labels abrufen
        labels_query = "CALL db.labels()"
        labels_result = await run_statement(labels_query)
        labels = [record["label"] for record in labels_result]

        # 2. Relationship-Typen abrufen
        rel_query = "CALL db.relationshipTypes()"
        rel_result = await run_statement(rel_query)
        rels = [record["relationshipType"] for record in rel_result]

        # 3. Properties (Detaillierte Übersicht)
        prop_query = "CALL db.schema.nodeTypeProperties()"
        props_result = await run_statement(prop_query)
        
        # Wir formatieren das Ergebnis etwas lesbarer
        schema_details = []
        for rec in props_result:
            schema_details.append({
                "nodeType": rec.get("nodeType"),
                "propertyName": rec.get("propertyName"),
                "propertyTypes": rec.get("propertyTypes")
            })

        return {
            "status": "success",
            "schema": {
                "available_labels": labels,
                "available_relationships": rels,
                "properties_overview": schema_details
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/data/units/{id}")
async def get_single_unit(id: str):
    """
    Liefert den komplexen Kontext für eine Unit ausgehend von ihrer unit_id.
    """
    try:
        # Wir rufen die komplexe Query aus der database.py auf
        result = await db.get_unit_by_id(id)

        return Response(content=result, media_type="text/markdown")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")