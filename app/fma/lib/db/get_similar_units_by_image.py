import httpx
from neo4j import AsyncGraphDatabase
import os

from .neo4j import db
from .tools.load_cypher_file import load_cypher_file
from .get_unit_by_id import get_unit_by_id

EMBEDDING_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://embed:8003/embed-image/")
driver = AsyncGraphDatabase.driver(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))

async def generate_embedding(image_bytes: bytes, filename: str = "image.jpg") -> list[float]:
    """Holt das Embedding vom Model-Container."""
    async with httpx.AsyncClient() as client:
        files = {'file': (filename, image_bytes, "image/jpeg")}
        response = await client.post(f"{EMBEDDING_URL}", files=files)
        response.raise_for_status()
        return response.json()["embedding"]

async def get_similar_units_by_image(image_bytes: bytes, filename: str = "image.jpg") -> str:
    """Führt die Vektorsuche durch und baut den Markdown-Report für das LLM."""
    
    # 1. Embedding generieren
    vector = await generate_embedding(image_bytes, filename)
    
    query = load_cypher_file("get_similar_units_by_image")
    
    async with driver.session() as session:
        result = await session.run(query, vector=vector)
        matches = await result.data()

    if not matches:
        return "Keine ausreichend ähnlichen Bilder in der Datenbank gefunden (Threshold < 0.5)."

    # 3. Schleife über die Ergebnisse und Markdown-Formatierung
    output = []
    
    for index, match in enumerate(matches, start=1):
        unit_id = match["unit_id"]
        composition_slug = match["composition_slug"]
        score = match["score"]
        
        # Hol die tiefgreifenden Infos über die eigene Funktion
        unit_details = await get_unit_by_id(unit_id)
        
        # Block zusammenbauen
        matched = f"## Match {index}\n"
        matched += f"**Similarity Score:** {score:.4f} | **Matching Composition:** {composition_slug}\n"
        matched += f"{unit_details}\n\n"

        output.append(matched)
        
    return "\n\n---\n\n".join(output)