MATCH (u:Unit)
WHERE u.unit_id = $id

MATCH path = (u)-[rels*1..10]->(target)
WHERE 
  NONE(rel IN relationships(path) WHERE 
    type(rel) CONTAINS 'PATTERN' OR 
    type(rel) CONTAINS 'PARALLEL' OR 
    type(rel) IN ['ASSERTED', 'HAS_COMPOSITION_COMPARISON']
  )
  AND
  NONE(node IN nodes(path)[1..-1] WHERE node:Concept)
  AND
  NONE(node IN nodes(path)[1..-1] WHERE node:Architectonic)
  AND
  NONE(node IN nodes(path) WHERE node:Image)

UNWIND relationships(path) AS r
WITH DISTINCT r
MATCH (start)-[r]->(end)

WITH start, r, end,
  apoc.convert.toJson(properties(start)) AS startProps,
  apoc.convert.toJson(properties(r)) AS relProps,
  apoc.convert.toJson(properties(end)) AS endProps
  
WITH 
  "(" + apoc.text.join(labels(start), ":") + " " + startProps + ") " +
  "-[:" + type(r) + " " + relProps + "]-> " +
  "(" + apoc.text.join(labels(end), ":") + " " + endProps + ")" AS line

RETURN apoc.text.join(collect(line), "\n* ") AS data