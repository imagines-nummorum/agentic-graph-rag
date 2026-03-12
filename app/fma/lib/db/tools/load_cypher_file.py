from pathlib import Path

def load_cypher_file(filename: str) -> str:
    """Liest eine .cypher Datei aus dem queries-Ordner ein."""
    filename = f"{filename}.cypher"
    query_path = Path(__file__).parent.parent / "queries" / filename
    with open(query_path, "r", encoding="utf-8") as f:
        return f.read().strip()