from ..mcp_registry import mcp_manager
from ...db.get_unit_by_id import get_unit_by_id
#from ...log.log_read_graph import log_read_graph

@mcp_manager.tool(
    name="get_unit_by_id",
    description="Holt Details zu einer Unit aus dem Graphen.",
    schema={
        "type": "object",
        "properties": {
            "id": {
                "oneOf": [
                    {"type": "integer"},
                    {"type": "string"}
                ],
                "description": "Einzelne Unit-ID."
            }
        },
        "required": ["id"]
    }
)
async def get_unit(args):
    unit_id = args.get("id")
    try:
        results = await get_unit_by_id(unit_id)
        return results
    except Exception as e:
        raise e