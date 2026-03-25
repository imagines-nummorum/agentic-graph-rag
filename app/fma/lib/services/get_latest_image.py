import sqlite3
import json
import base64

def get_latest_image(session_id: str = None) -> bytes:
    """
    Liest das neueste Bild aus der gemounteten ADK SQLite-Datenbank aus.
    Gibt die rohen Bytes des Bildes zurück (oder None, falls keins gefunden wurde).
    """
    # Read-Only URI mit 5 Sekunden Timeout für sichere Nebenläufigkeit (Concurrency)
    # Passe den Pfad an deinen Docker-Mount an!
    db_path = "/adk/Analyzer/.adk/session.db" 
    
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
        cursor = conn.cursor()
        
        # Wir suchen gezielt nach den neuesten Events (optional gefiltert nach Session)
        if session_id:
            query = "SELECT event_data FROM events WHERE session_id = ? ORDER BY timestamp DESC"
            cursor.execute(query, (session_id,))
        else:
            query = "SELECT event_data FROM events ORDER BY timestamp DESC"
            cursor.execute(query)

        # Iteriere durch die neuesten Events
        for row in cursor.fetchall():
            
            try:
                event_data = json.loads(row[0])
                content = event_data.get("content", {})
                parts = content.get("parts", [])
                
                for part in parts:
                    if "inline_data" in part:
                        inline_data = part["inline_data"]
                        
                        # --- NEU: Der Türsteher ---
                        mime_type = inline_data.get("mime_type", "")
                        if not mime_type.startswith("image/"):
                            # Ist z.B. application/pdf, wir ignorieren es und suchen weiter
                            continue
                            
                        # Metadaten abgreifen (super für dein Logging!)
                        filename = inline_data.get("display_name", "unbekanntes_bild")
                        base64_string = inline_data.get("data")
                        
                        if not base64_string:
                            continue
                            
                        # 1. Prefix abschneiden
                        if "," in base64_string:
                            base64_string = base64_string.split(",", 1)[1]

                        # 2. Brutal bereinigen
                        base64_string = base64_string.replace('\n', '').replace('\r', '').replace(' ', '')
                        base64_string = base64_string.replace('-', '+').replace('_', '/')

                        # 3. Vorhandenes Padding am Ende entfernen
                        base64_string = base64_string.rstrip('=')

                        # 4. DIE BRECHSTANGE
                        if len(base64_string) % 4 == 1:
                            base64_string = base64_string[:-1]

                        # 5. Sauberes Padding wieder hinzufügen
                        padding_needed = len(base64_string) % 4
                        if padding_needed > 0:
                            base64_string += '=' * (4 - padding_needed)

                        # 6. Decodieren
                        try:
                            image_bytes = base64.b64decode(base64_string)
                            conn.close()
                            
                            print(f"DEBUG - FMA: Latest image requested, found {filename} ({mime_type})")
                            
                            # Optional: Du könntest hier auch ein Tuple zurückgeben 
                            # return image_bytes, mime_type
                            return image_bytes
                            
                        except Exception as e:
                            print(f"Fehler beim Decodieren von {filename}: {e}")
                            continue
                            
            except json.JSONDecodeError:
                continue
                        
            except json.JSONDecodeError:
                continue
                
    except sqlite3.OperationalError as e:
        print(f"Datenbank-Fehler (z.B. gelockt): {e}")
    finally:
        # Sicherstellen, dass die Verbindung immer geschlossen wird
        if 'conn' in locals():
            conn.close()
            
    return None # Kein Bild gefunden