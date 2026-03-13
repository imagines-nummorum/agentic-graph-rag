
import os
import glob
import httpx
import io
from PIL import Image

from .get_similar_units_by_image import get_similar_units_by_image

# --- Sicherheits-Konfiguration ---
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB Limit
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]

async def fetch_and_validate_image(url: str) -> bytes:
    """Lädt ein Bild über eine URL herunter und prüft es auf Sicherheit und Integrität."""
    
    # httpx.AsyncClient mit strengem Timeout
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Wir nutzen einen Stream, um nicht sofort die ganze Datei in den RAM zu ziehen
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            
            # 1. Header-Check: Ist das überhaupt ein Bild?
            content_type = response.headers.get("Content-Type", "")
            if not any(mime in content_type for mime in ALLOWED_MIME_TYPES):
                raise ValueError(f"Abgelehnter Content-Type: {content_type}. Erlaubt sind nur JPG, PNG und WEBP.")
            
            # 2. Header-Check: Ist die Datei zu groß?
            content_length = int(response.headers.get("Content-Length", 0))
            if content_length > MAX_IMAGE_SIZE:
                raise ValueError(f"Datei ist zu groß ({content_length} Bytes). Erlaubt sind maximal 10 MB.")

            # 3. Chunked Download (Schützt vor gefälschten Content-Length Headern)
            image_bytes = bytearray()
            async for chunk in response.aiter_bytes():
                image_bytes.extend(chunk)
                if len(image_bytes) > MAX_IMAGE_SIZE:
                    raise ValueError("Download abgebrochen: Die Datei überschreitet das Limit von 10 MB.")

    # 4. Deep Inspection: Prüfen der "Magic Bytes" (Header-Signatur der Datei)
    try:
        # verify() lädt nicht das ganze Bild, sondern checkt nur die Integrität der Header
        img = Image.open(io.BytesIO(image_bytes))
        img.verify() 
    except Exception as e:
        raise ValueError("Die heruntergeladene Datei ist kein valides oder beschädigtes Bild.")

    return bytes(image_bytes)
    
async def get_similar_units_by_url(image_url: str) -> str:
    
    try:
        # Sicheren Download und Validierung aufrufen
        image_bytes = await fetch_and_validate_image(image_url)
        
        # An die saubere Core-Logik übergeben
        output = await get_similar_units_by_image(image_bytes)

        return output
        
    except ValueError as ve:
        # Unsere eigenen Sicherheits-Exceptions an das LLM zurückmelden
        return f"Sicherheitsblockade: {str(ve)} Bitte nutze eine andere URL."
    except httpx.HTTPError as he:
        # Netzwerkfehler (z.B. 404 Not Found)
        return f"Netzwerkfehler beim Abruf der URL: {str(he)}"
    except Exception as e:
        # Generische Fehler
        return f"Systemfehler bei der Verarbeitung des Bildes: {str(e)}"