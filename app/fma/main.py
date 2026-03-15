import os
import uuid
import asyncio
from contextlib import asynccontextmanager
from typing import Union, List, Annotated

from fastapi import FastAPI, Response, Request, HTTPException, Depends, Query, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from mcp.server.sse import SseServerTransport

# WICHTIG: Hier importieren wir die Logik
from .lib.mcp.mcp_server import mcp_server
from .lib.db.neo4j import db

from .lib.mcp.tools.prompts import onboarding_briefing

from .lib.db.get_graph_schema import get_graph_schema
from .lib.db.get_unit_by_id import get_unit_by_id
from .lib.db.get_similar_units_by_image import get_similar_units_by_image
from .lib.db.get_similar_units_by_url import get_similar_units_by_url

from .lib.services.get_latest_image import get_latest_image

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

# --- Static / HTML ---

app.mount("/static", StaticFiles(directory="/app/app/static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/catalogue", response_class=HTMLResponse)
async def read_root(request: Request):
    # 'request' muss zwingend an das Template übergeben werden
    return templates.TemplateResponse(
        request=request, name="catalogue.html", context={"id": "Prototype 1.0"}
    )


# --- REST ---
@app.get("/")
async def root():
    return {"status": "online", "modes": ["REST", "MCP-SSE"]}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/prompts/onboarding")
async def show_onboarding_prompt():
    output = await onboarding_briefing()
    return Response(content=output, media_type="text/markdown")

@app.get("/graph/schema")
async def show_graph_schema():
    """
    Gibt eine Übersicht über alle Labels, Relationships 
    und deren Properties im Graphen zurück.
    """
    try:
        schema = await get_graph_schema()

        return {
            "status": "success",
            "schema": schema
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/data/units/{id}")
async def get_single_unit(id: str):
    """
    Shows complete content for one unit, optimized for LLMs.
    """
    try:
        # Wir rufen die komplexe Query aus der database.py auf
        result = await get_unit_by_id(id)

        return Response(content=result, media_type="text/markdown")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@app.post("/find/similar-units-by-file/")
async def find_similar_units_by_file(file: UploadFile = File(...)):
    """
    Shows the 3 most similar image descriptions matching the uploaded file.
    """
    image_bytes = await file.read()
    result = await get_similar_units_by_image(image_bytes)
    
    return Response(content=result, media_type="text/markdown")

@app.post("/find/similar-units-by-url/")
async def find_similar_units_by_url(url: str):
    """
    Shows the 3 most similar image descriptions matching the provided url.
    """
    result = await get_similar_units_by_url(url)
    
    return Response(content=result, media_type="text/markdown")

STAGING_DIR = "/app/app/tmp/staged_images"
os.makedirs(STAGING_DIR, exist_ok=True)

@app.post("/stage-image/")
async def stage_image(file: UploadFile = File(...)):
    """
    Nimmt ein Bild entgegen, speichert es kurzzeitig und gibt eine Asset-ID für das MCP zurück.
    """
    # Generiere eine eindeutige ID
    asset_id = str(uuid.uuid4())
    
    # Speichere die Datei mit der ID als Präfix, damit wir den Originalnamen behalten
    file_path = os.path.join(STAGING_DIR, f"{asset_id}_{file.filename}")
    
    # Datei auf die "flüchtige" Platte schreiben
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    return {
        "asset_id": asset_id, 
        "filename": file.filename, 
        "message": "Image staged"
    }

@app.get("/latest-image/")
async def show_latest_image():
    string = get_latest_image()
    return Response(content=string, media_type="text/plaintext")