from .neo4j import db

async def get_graph_schema():
    """
    Gibt eine Übersicht über alle Labels, Relationships 
    und deren Properties im Graphen zurück.
    """
    # 1. Labels abrufen
    labels_query = "CALL db.labels()"
    labels_result = await db.run_statement(labels_query)
    labels = [record["label"] for record in labels_result]

    # 2. Relationship-Typen abrufen
    rel_query = "CALL db.relationshipTypes()"
    rel_result = await db.run_statement(rel_query)
    rels = [record["relationshipType"] for record in rel_result]

    # 3. Properties (Detaillierte Übersicht)
    prop_query = "CALL db.schema.nodeTypeProperties()"
    props_result = await db.run_statement(prop_query)
    
    # Wir formatieren das Ergebnis etwas lesbarer
    schema_details = []
    for rec in props_result:
        schema_details.append({
            "nodeType": rec.get("nodeType"),
            "propertyName": rec.get("propertyName"),
            "propertyTypes": rec.get("propertyTypes")
        })

    return {
        "available_labels": labels,
        "available_relationships": rels,
        "properties_overview": schema_details
    }