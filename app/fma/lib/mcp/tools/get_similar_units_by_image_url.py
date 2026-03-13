
import os
import glob
import httpx
import io
from PIL import Image

from ..mcp_registry import mcp_manager
from ...db.get_similar_units_by_url import get_similar_units_by_url

@mcp_manager.tool(
    name="get_similar_units_by_image_url",
    description="Sucht anhand einer Image-URL nach den maximal 3 ähnlichsten Bildern im Knowledge Graph.",
    schema={
        "type": "object",
        "properties": {
            "image_url": {
                "type": "string",
                "description": "Die eindeutige Image-ID des Bildes."
            }
        },
        "required": ["image_url"]
    }
)
async def get_similar_units_by_image_url(image_url: dict | str) -> str:
    
    if isinstance(image_url, dict):
        actual_url = image_url.get("image_url")
    else:
        actual_url = image_url
        
    if not actual_url:
        return "Systemhinweis: Tool-Aufruf fehlgeschlagen. Keine 'image_url' übergeben."
    
    return await get_similar_units_by_url(actual_url)