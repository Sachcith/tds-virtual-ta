import os
import json
import base64
import time

import numpy as np
from flask import Flask, request, jsonify, render_template
from huggingface_hub import InferenceClient

app = Flask(__name__)

# ─── Initialize the HF InferenceClient ────────────────────────────────────────
client = InferenceClient(
    provider="hf-inference",
    api_key=os.environ["HF_TOKEN"],
)

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ─── Load your scraped Discourse posts ────────────────────────────────────────
with open("discourse_posts.json") as f:
    posts = json.load(f)

titles = [p["title"] for p in posts]
urls   = [f"https://discourse.onlinedegree.iitm.ac.in/t/{p['id']}" for p in posts]


# ─── Replace get_embedding with InferenceClient.feature_extraction ────────────
def get_embedding(text: str) -> list[float]:
    try:
        # client.feature_extraction returns a list of lists (batch of 1)
        result = client.feature_extraction(
            text,
            model=EMBED_MODEL
        )
        print("Length:", len(result))
        print("Sample:", result[:5])
        # unwrap the batch
        return result
    except Exception as e:
        print("Error in get_embedding:", e)
        return []


# ─── Precompute title embeddings once ────────────────────────────────────────
if os.path.exists("title_embeddings.json"):
    with open("title_embeddings.json") as f:
        title_embeddings = json.load(f)
else:
    title_embeddings = []
    a = 1
    for title in titles:
        print(a)
        a+=1
        vec = get_embedding(title)
        if isinstance(vec, np.ndarray):  # Convert if it's a NumPy array
            vec = vec.tolist()
        title_embeddings.append(vec)

    with open("title_embeddings.json", "w") as f:
        json.dump(title_embeddings, f)


# ─── Flask routes ─────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def root():
    return render_template("index.html")


@app.route("/api/", methods=["POST"])
def answer():
    data      = request.get_json()
    question  = data.get("question")
    image_b64 = data.get("image")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    # optional: save image if provided
    if image_b64:
        header, b64data = (image_b64.split(",", 1)
                           if "," in image_b64 else (None, image_b64))
        img_bytes = base64.b64decode(b64data)
        os.makedirs("uploads", exist_ok=True)
        path = f"uploads/{int(time.time())}.webp"
        with open(path, "wb") as f:
            f.write(img_bytes)

    # 1) get question embedding
    q_embed = np.array(get_embedding(question))
    if q_embed.shape != (384,):
        return jsonify({"error": "Failed to embed question"}), 500

    # 2) compute cosine similarities
    def cosine(a, b):
        a, b = np.array(a), np.array(b)
        if np.linalg.norm(a)==0 or np.linalg.norm(b)==0:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a)*np.linalg.norm(b)))

    sims = [cosine(q_embed, t) for t in title_embeddings]

    # 3) pick top‑2
    top2 = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:2]
    links = [{"url": urls[i], "text": titles[i]} for i in top2]

    answer_text = f"Here's what I found: '{question}'"
    return jsonify({"answer": answer_text, "links": links})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
