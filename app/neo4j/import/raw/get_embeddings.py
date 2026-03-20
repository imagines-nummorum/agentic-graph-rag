import re
import os
import requests
from urllib.parse import urlparse

# --- Konfiguration ---
INPUT_CYPHER = "../99_data.cypher"
OUTPUT_CYPHER = "../99b_embeddings.cypher"
IMAGE_DIR = "../../../fma/static/img"
EMBEDDING_API = "http://localhost:8002/embed-image/"


def extract_image_data(filepath: str) -> list[dict]:
    """Sucht nach slug und src_url innerhalb von :Image Knoten."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Finde alle Eigenschafts-Blöcke von Image-Knoten: :Image { ... }
    node_pattern = r':Image\s*\{([^}]+)\}'
    blocks = re.findall(node_pattern, content)
    
    image_data = []
    for block in blocks:
        # 2. Extrahiere slug und src_url aus dem Block
        slug_match = re.search(r'name:\s*"([^"]+)"', block)
        url_match = re.search(r'src_url:\s*"([^"]+)"', block)
        
        if slug_match and url_match:
            image_data.append({
                "slug": slug_match.group(1),
                "src_url": url_match.group(1)
            })
            
    # Deduplizieren anhand des Slugs (falls Einträge im Dump mehrfach auftauchen)
    unique_data = {item["slug"]: item for item in image_data}.values()
    return list(unique_data)

def main():
    images = extract_image_data(INPUT_CYPHER)
    print(f"{len(images)} eindeutige Bild-Knoten gefunden. Starte Harvesting...")

    with open(OUTPUT_CYPHER, 'w', encoding='utf-8') as out_f:
        out_f.write("// Automatisch generiertes Skript für Image Embeddings\n\n")

        for img in images:
            slug = img["slug"]
            url = img["src_url"]
            print(f"Verarbeite: {slug}")
            
            # 1. Bild herunterladen
            try:
                img_response = requests.get(url, timeout=10)
                img_response.raise_for_status()
                img_bytes = img_response.content
            except requests.RequestException as e:
                print(f"  -> Fehler beim Download von {url}: {e}")
                continue

            # 2. Dateinamen aus Slug generieren (Dateiendung aus URL übernehmen)
            extension = os.path.splitext(urlparse(url).path)[1] or ".jpg"
            filename = f"{slug}{extension}"
            local_path = os.path.join(IMAGE_DIR, filename)

            # 3. Bild lokal speichern
            with open(local_path, 'wb') as f:
                f.write(img_bytes)

            # 4. Embedding vom Container holen
            try:
                files = {'file': (filename, img_bytes, 'image/jpeg')}
                emb_response = requests.post(EMBEDDING_API, files=files)
                emb_response.raise_for_status()
                embedding_vector = emb_response.json().get("embedding")
            except requests.RequestException as e:
                print(f"  -> Fehler beim Embedding für {slug}: {e}")
                continue

            # 5. Cypher-Update-Statement generieren (gemappt über src_url)
            cypher_stmt = f"""MATCH (i:Image {{src_url: "{url}"}})
SET i.embedding = {embedding_vector};
"""
            out_f.write(cypher_stmt + "\n")
            
    print(f"Fertig! Update-Skript wurde unter {OUTPUT_CYPHER} gespeichert.")

if __name__ == "__main__":
    main()