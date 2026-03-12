import os
import asyncio
from neo4j import AsyncGraphDatabase

from .tools.validate_read import is_read_only
from .tools.serialize_records import serialize_records
from .tools.load_cypher_file import load_cypher_file
from .tools.reduce_unit_for_llm import reduce_unit_for_llm

#from .queries.get_units import GET_UNITS_BY_ID

# Umgebungsvariablen (werden aus docker-compose gefüttert)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

class GraphDatabase:
    def __init__(self):
        self.driver = None

    def connect(self):
        self.driver = AsyncGraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    async def close(self):
        if self.driver:
            await self.driver.close()

    async def run_statement(self, query: str, parameters: dict = None):
        if not self.driver:
            self.connect()
        
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def run_query(self, query: str, parameters: dict = None):
    
        if not is_read_only(query):
            return {
                "error": "true", 
                "message": "Validation Error: This Graph is read-only."
            }
            
        if not self.driver:
            self.connect()
        
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
        
            output = []
            async for record in result:
                # Wir serialisieren jedes Feld im Record einzeln
                serialized_record = {
                    key: await serialize_records(val) 
                    for key, val in record.items()
                }
                output.append(serialized_record)
                
            return output

    async def get_unit_by_id(self, unit_id):
        """Sucht Unit basierend auf ID."""

        int(unit_id) if unit_id.isdigit() else unit_id
        
        query = load_cypher_file("get_unit_by_id")
        result = await self.run_statement(query, {"id": unit_id})
        
        if not result[0]["data"]:
            return f"Unit '{unit_id}' not found"

        return reduce_unit_for_llm(result[0]["data"])

db = GraphDatabase()

async def run_statement(query: str, parameters: dict = None):
    return await db.run_statement(query, parameters)

async def run_query(query: str, parameters: dict = None):
    return await db.run_query(query, parameters)

async def get_unit_by_id(unit_id):
    return await db.get_unit_by_id(unit_id)