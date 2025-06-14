from flask import Flask, request, jsonify, render_template
import base64, os, json, requests

app = Flask(__name__)

# Hugging Face API setup
HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
HF_HEADERS = {
    "Authorization": f"Bearer {os.getenv('HF_TOKEN')}"  # Set this in your Render environment
}

# Load saved posts
with open("discourse_posts.json") as f:
    posts = json.load(f)

# Prepare titles and URLs
titles = [p['title'] for p in posts]
urls = [f"https://discourse.onlinedegree.iitm.ac.in/t/{p['id']}" for p in posts]

# Function to get embedding from Hugging Face API
def get_embedding(text):
    response = requests.post(HF_API_URL, headers=HF_HEADERS, json={"inputs": text})
    response.raise_for_status()
    return response.json()[0]  # List[float]

# Pre-compute embeddings for all titles (run once at startup)
import numpy as np
title_embeddings = [get_embedding(t) for t in titles]

@app.route("/", methods=["GET","POST"])
def root():
    return render_template("index.html")

@app.route("/api/", methods=["POST"])
def answer():
    data = request.get_json()
    question = data.get("question")
    image_b64 = data.get("image", None)

    if not question:
        return jsonify({"error": "Question is required"}), 400

    # Get question embedding
    q_embed = np.array(get_embedding(question))

    # Cosine similarity search
    sims = [np.dot(q_embed, np.array(t)) / (np.linalg.norm(q_embed) * np.linalg.norm(t)) for t in title_embeddings]
    top_k_idx = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:2]

    links = []
    for idx in top_k_idx:
        links.append({
            "url": urls[idx],
            "text": titles[idx]
        })

    answer_text = f"Here's what I found based on your question: '{question}'"

    return jsonify({
        "answer": answer_text,
        "links": links
    })

PORT = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=PORT, debug=True)