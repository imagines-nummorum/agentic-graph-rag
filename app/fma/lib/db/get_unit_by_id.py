from .neo4j import db
from .tools.load_cypher_file import load_cypher_file
from .tools.reduce_unit_for_llm import reduce_unit_for_llm

async def get_unit_by_id(unit_id):
    """Sucht Unit basierend auf ID."""

    # ensure INTs are handled as such
    if isinstance(unit_id, str) and unit_id.isdigit():
        unit_id = int(unit_id)
    
    query = load_cypher_file("get_unit_by_id")
    result = await db.run_statement(query, {"id": unit_id})
    
    if not result[0]["data"]:
        return f"Unit '{unit_id}' not found"

    return reduce_unit_for_llm(result[0]["data"])