#!/bin/bash

# Konfiguration
SERVICE_NAME="neo4j" # Name deines Services in docker-compose
USER="neo4j"
PASS="password"
IMPORT_DIR="./app/neo4j/import" # Pfad auf deinem Host

# Hilfsfunktion zum Zählen der Nodes
get_node_count() {
    # --format plain sorgt für eine saubere Ausgabe ohne Tabellenrahmen
    # tail -n 1 extrahiert nur den reinen Zahlenwert
    docker compose exec -T $SERVICE_NAME cypher-shell -u $USER -p $PASS --format plain "MATCH (n) RETURN count(n);" | tail -n 1
}

echo ""
echo "--- Populating Neo4j ---"

# 1. Schritt: Datenbank leeren
START_COUNT=$(get_node_count)
echo ""
echo "Droping existing nodes ..."
docker compose exec -T $SERVICE_NAME cypher-shell -u $USER -p $PASS "MATCH (n) DETACH DELETE n;"

# 2. Schritt: Bestätigung nach Löschen
CLEAN_COUNT=$(get_node_count)
echo "Done: $CLEAN_COUNT nodes ($START_COUNT deleted)"

# 3. Schritt: Scripte alphabetisch einspielen
# 'ls' sortiert standardmäßig alphabetisch.
echo ""
echo "Start importing Cypher files..."

files=$(printf '%s\n' "$IMPORT_DIR"/*.cypher | LC_ALL=C sort)

for file in $files; do
    filename=$(basename "$file")
    echo ""
    echo "  $filename ..."
    
    # Hier wird das Script im Container ausgeführt
    # Der Output von cypher-shell wird direkt im Terminal angezeigt
    docker compose exec -T $SERVICE_NAME cypher-shell -u $USER -p $PASS -f "/import/$filename"
    
    if [ $? -eq 0 ]; then
        echo "  Done!"
    else
        echo "  Error!"
    fi
    sleep 1
done

# 4. Schritt: Finaler Count
FINAL_COUNT=$(get_node_count)
echo ""
echo "Import finished: $FINAL_COUNT Nodes created"
echo ""