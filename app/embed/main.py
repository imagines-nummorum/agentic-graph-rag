from fastapi import FastAPI, UploadFile, File
from sentence_transformers import SentenceTransformer
from PIL import Image
import io

app = FastAPI(title="Image Embedding Service")

# Lädt das CLIP-Modell (beim Start des Containers)
# clip-ViT-B-32 erzeugt Vektoren mit 512 Dimensionen
model = SentenceTransformer('clip-ViT-B-32') 

@app.post("/embed-image/")
async def embed_image(file: UploadFile = File(...)):
    # Bild in den Speicher laden
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    
    # Embedding generieren (als Liste zurückgeben, ideal für JSON)
    embedding = model.encode(image).tolist()
    
    return {"embedding": embedding, "dimensions": len(embedding)}