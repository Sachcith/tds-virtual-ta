from flask import Flask, request, jsonify, render_template
import base64, os, json, requests
import numpy as np

app = Flask(__name__)

# ✅ Fixed HF model endpoint
HF_API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
HF_HEADERS = {
    "Authorization": f"Bearer {os.getenv('HF_TOKEN')}"  # Set in Render or .env
}

# Load saved posts
with open("discourse_posts.json") as f:
    posts = json.load(f)

# Prepare titles and URLs
titles = [p['title'] for p in posts]
urls = [f"https://discourse.onlinedegree.iitm.ac.in/t/{p['id']}" for p in posts]

# Function to get embedding from Hugging Face API
def get_embedding(text: str) -> list[float]:
    try:
        response = requests.post(
            HF_API_URL,
            headers=HF_HEADERS,
            json={"inputs": text}  # for sentence-transformers, inputs = string
        )
        response.raise_for_status()
        return response.json()  # returns a flat list [float]
    except Exception as e:
        print("Error in get_embedding:", e)
        return []

# Pre-compute title embeddings
title_embeddings = []
for title in titles:
    vec = get_embedding(title)
    if vec:
        title_embeddings.append(vec)
    else:
        title_embeddings.append(np.zeros(384))  # fallback zero vector

@app.route("/", methods=["GET", "POST"])
def root():
    return render_template("index.html")

@app.route("/api/", methods=["POST"])
def answer():
    data = request.get_json()
    question = data.get("question")
    image_b64 = data.get("image", None)

    if not question:
        return jsonify({"error": "Question is required"}), 400

    q_embed = np.array(get_embedding(question))
    if len(q_embed) == 0:
        return jsonify({"error": "Failed to get embedding from HF API"}), 500

    # Cosine similarity
    sims = [np.dot(q_embed, np.array(t)) / (np.linalg.norm(q_embed) * np.linalg.norm(t)) for t in title_embeddings]
    top_k_idx = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:2]

    links = [{"url": urls[i], "text": titles[i]} for i in top_k_idx]
    answer_text = f"Here's what I found based on your question: '{question}'"

    return jsonify({"answer": answer_text, "links": links})

PORT = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=PORT, debug=True)
