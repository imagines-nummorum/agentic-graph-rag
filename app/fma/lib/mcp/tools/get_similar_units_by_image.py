
import base64
import os
import glob

from ..mcp_registry import mcp_manager
from ...db.get_similar_units_by_image import get_similar_units_by_image as get_similar
from ...services.get_latest_image import get_latest_image

STAGING_DIR = "/app/app/tmp/staged_images"

@mcp_manager.tool(
    name="get_similar_units_by_image",
    description="Sucht anhand des zuvor hochgeladenen Bilds nach den maximal 3 ähnlichsten Bildern im Knowledge Graph.",
    schema={
        "type": "object",
        "properties": {}, # Keine Argumente mehr nötig!
        "required": []
    }
)
async def get_similar_units_by_image(args=None) -> str:
    image_bytes = get_latest_image()
    return await get_similar(image_bytes)