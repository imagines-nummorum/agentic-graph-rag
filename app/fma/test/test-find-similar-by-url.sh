#!/bin/bash

# --- Konfiguration ---
# Passe den Port an, falls dein Container auf einem anderen Port lauscht
API_URL="http://localhost:8001/find/similar-units-by-url/"
IMAGE_PATH=$1

# 1. Prüfen, ob ein Argument übergeben wurde
if [ -z "$IMAGE_PATH" ]; then
    echo "Bitte gib den Pfad zu einem Testbild an."
    echo "Nutzung: ./test_embedding.sh <pfad_zum_bild.jpg>"
    exit 1
fi

# 2. Prüfen, ob die Datei lokal existiert
if [ ! -f "$IMAGE_PATH" ]; then
    echo "Fehler: Die Datei '$IMAGE_PATH' wurde nicht gefunden!"
    exit 1
fi

echo "Sende Bild '$IMAGE_PATH' an $API_URL ..."
echo "---------------------------------------------------"

# 3. Der eigentliche Curl-Befehl
# -s versteckt den Ladebalken von curl
# -F sendet das Bild als multipart/form-data unter dem Feldnamen "file"
curl -s -X POST "$API_URL" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@$IMAGE_PATH"

echo -e "\n\n---------------------------------------------------"
echo "Fertig."