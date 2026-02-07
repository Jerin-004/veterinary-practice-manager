from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import gzip
import pickle
import numpy as np
import requests
import qrcode
import os
from dotenv import load_dotenv
load_dotenv()


# ---------------- APP INIT ----------------
app = FastAPI(title="Veterinary Practice Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_TOKEN = os.getenv("HF_TOKEN")
from huggingface_hub import InferenceClient

hf_client = InferenceClient(
    model="sentence-transformers/all-MiniLM-L6-v2",
    token=HF_TOKEN
)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("data.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_name TEXT,
    compressed_note BLOB,
    embedding BLOB
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS protocols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    steps TEXT,
    embedding BLOB
)
""")

conn.commit()

# ---------------- UTILS ----------------
def compress_text(text: str) -> bytes:
    return gzip.compress(text.encode())

def decompress_text(data: bytes) -> str:
    return gzip.decompress(data).decode()

def serialize_embedding(vec) -> bytes:
    return pickle.dumps(vec)

def deserialize_embedding(blob: bytes):
    return pickle.loads(blob)

# def embed(text: str):
#     url = (
#         "https://router.huggingface.co/hf-inference/models/"
#         "sentence-transformers/all-MiniLM-L6-v2"
#     )

#     response = requests.post(
#         url,
#         headers={
#             "Authorization": f"Bearer {HF_TOKEN}",
#             "Content-Type": "application/json"
#         },
#         json={
#             "inputs": [text],               # 👈 IMPORTANT: LIST
#             "options": {"wait_for_model": True}
#         },
#         timeout=30
#     )

#     if response.status_code != 200:
#         raise RuntimeError(
#             f"HF API error {response.status_code}: {response.text}"
#         )

#     data = response.json()

#     # HF returns: [[embedding]]
#     return data[0]


def embed(text: str):
    embedding = hf_client.feature_extraction(
        text,
        normalize=True
    )
    return embedding

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)

    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0

    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# ---------------- SEED PROTOCOLS ----------------
def seed_protocols():
    cur.execute("SELECT COUNT(*) FROM protocols")
    if cur.fetchone()[0] > 0:
        return

    protocols = [
        ("Canine Fever", "Rest, fluids, antipyretics"),
        ("Respiratory Infection", "Antibiotics, steam therapy"),
        ("Vaccination Protocol", "Standard immunization schedule"),
        ("Digestive Disorder", "Diet control and hydration")
    ]

    for title, steps in protocols:
        emb = embed(title + " " + steps)
        cur.execute(
            "INSERT INTO protocols (title, steps, embedding) VALUES (?, ?, ?)",
            (title, steps, serialize_embedding(emb))
        )

    conn.commit()

# seed_protocols()

# ---------------- MODELS ----------------
class RecordIn(BaseModel):
    pet_name: str
    note: str

# ---------------- API ENDPOINTS ----------------

@app.post("/add-record")
def add_record(data: RecordIn):
    compressed = compress_text(data.note)
    embedding = embed(data.note)

    cur.execute(
        "INSERT INTO records (pet_name, compressed_note, embedding) VALUES (?, ?, ?)",
        (data.pet_name, compressed, serialize_embedding(embedding))
    )
    conn.commit()

    return {"message": "Medical record stored (compressed)"}

@app.post("/suggest-protocol")
def suggest_protocol(note: str = Query(...)):
    query_emb = embed(note)

    cur.execute("SELECT title, steps, embedding FROM protocols")
    rows = cur.fetchall()

    scored = []
    for title, steps, emb_blob in rows:
        proto_emb = deserialize_embedding(emb_blob)
        score = cosine_similarity(query_emb, proto_emb)
        scored.append((score, title, steps))

    scored.sort(reverse=True)

    return [
        {
            "title": title,
            "steps": steps,
            "similarity": round(score, 2)
        }
        for score, title, steps in scored[:2]
    ]

@app.get("/qr/{pet_name}")
def generate_qr(pet_name: str):
    os.makedirs("qrcodes", exist_ok=True)
    url = f"http://localhost:5173/emergency/{pet_name}"
    path = f"qrcodes/{pet_name}.png"

    img = qrcode.make(url)
    img.save(path)

    return FileResponse(path)

@app.get("/emergency/{pet_name}")
def emergency_view(pet_name: str):
    cur.execute(
        "SELECT compressed_note FROM records WHERE pet_name = ? ORDER BY id DESC LIMIT 1",
        (pet_name,)
    )
    row = cur.fetchone()

    if not row:
        return {"error": "No record found"}

    return {
        "pet_name": pet_name,
        "last_note": decompress_text(row[0])
    }

@app.on_event("startup")
def startup_event():
    try:
        seed_protocols()
    except Exception as e:
        print("Protocol seeding failed:", e)
