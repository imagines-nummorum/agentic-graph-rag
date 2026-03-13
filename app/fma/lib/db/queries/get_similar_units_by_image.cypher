CALL db.index.vector.queryNodes('image_embeddings_index', 3, $vector) 
    YIELD node AS img, score
    WHERE score >= 0.5
    
    // Pfad zur Unit basierend auf deinem Cypher-Schema auflösen
    MATCH (img)<-[:HAS_IMAGE]-(comp:Composition)<-[:HAS_COMPOSITION]-(unit:Unit)
    
    RETURN 
        unit.unit_id AS unit_id, 
        comp.slug AS composition_slug, 
        score
    ORDER BY score DESC