
import base64
import os
import glob

from ..mcp_registry import mcp_manager
from ...db.get_similar_units_by_image import get_similar_units_by_image

STAGING_DIR = "/app/app/tmp/staged_images"

@mcp_manager.tool(
    name="get_similar_units_by_asset_id",
    description="Sucht anhand der asset_id des zuvor hochgeladenen Bilds nach den maximal 3 ähnlichsten Bildern im Knowledge Graph.",
    schema={
        "type": "object",
        "properties": {
            "asset_id": {
                "type": "string",
                "description": "Die eindeutige Image-ID des Bildes."
            }
        },
        "required": ["asset_id"]
    }
)
async def get_similar_units_by_asset_id(asset_id: dict | str) -> str:
    # --- FIX: Das Framework-Objekt auspacken ---
    if isinstance(asset_id, dict):
        actual_id = asset_id.get("asset_id")
    else:
        actual_id = asset_id
        
    if not actual_id:
        return "Systemhinweis: Tool-Aufruf fehlgeschlagen. Keine 'asset_id' übergeben."
    
    # -------------------------------------------
    # 1. Datei suchen
    search_pattern = os.path.join(STAGING_DIR, f"{actual_id}_*")
    matches = glob.glob(search_pattern)
    
    if not matches:
        return f"ERROR: No Image found for Image-ID '{actual_id}'."
        
    file_path = matches[0]
    
    try:
        # 2. In den RAM laden
        with open(file_path, "rb") as f:
            image_bytes = f.read()
            
    finally:
        print(f"Requested: {file_path}")
    #    # 3. GARBAGE COLLECTION: Physische Datei sofort löschen
    #    if os.path.exists(file_path):
    #        os.remove(file_path)
            
    # 4. Saubere Core-Logik aufrufen (mit den Bytes im RAM)
    return await get_similar_units_by_image(image_bytes)