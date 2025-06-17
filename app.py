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
            json={"inputs": text}
        )
        response.raise_for_status()
        vec = response.json()
        if isinstance(vec, list) and isinstance(vec[0], list):
            return vec[0]  # <-- ✅ Flatten 2D to 1D
        return vec
    except Exception as e:
        print("Error in get_embedding:", e)
        return []

# Pre-compute title embeddings
if os.path.exists("title_embeddings.json"):
    with open("title_embeddings.json") as f:
        title_embeddings = json.load(f)
else:
    title_embeddings = []
    for title in titles:
        vec = get_embedding(title)
        print(title, len(vec), vec[:5])
        if vec:
            title_embeddings.append(vec)
        else:
            title_embeddings.append([0.0] * 384)
    with open("title_embeddings.json", "w") as f:
        json.dump(title_embeddings, f)

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

    # Get question embedding
    q_embed = np.array(get_embedding(question))
    if q_embed.shape[0] != 384:
        return jsonify({"error": "Failed to get valid embedding from HF API"}), 500

    print(f"✅ Question: {question}")
    print(f"✅ Embedding (shape): {q_embed.shape}")
    print(f"✅ Embedding (first 5 values): {q_embed[:5]}")

    # Cosine similarity with safe handling
    def cosine_sim(a, b):
        a = np.array(a)
        b = np.array(b)
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    sims = [cosine_sim(q_embed, t) for t in title_embeddings]

    # Debug: check for NaNs
    for idx, sim in enumerate(sims):
        if not np.isfinite(sim):
            print(f"⚠ Invalid similarity at idx {idx}: {sim} (title: {titles[idx]})")

    # Sort and filter
    top_k_idx = sorted(
        [i for i in range(len(sims)) if np.isfinite(sims[i])],
        key=lambda i: sims[i],
        reverse=True
    )
    print(len(sims))
    if not top_k_idx:
        print("⚠ No valid similarity scores found.")
        return jsonify({"answer": f"No relevant posts found for your question: '{question}'", "links": []})

    print("✅ Top 5 similarities:")
    for i in top_k_idx[:5]:
        print(f"  - Score: {sims[i]:.4f} | Title: {titles[i]}")

    # Build links
    links = [{"url": urls[i], "text": titles[i]} for i in top_k_idx[:2]]
    answer_text = f"Here's what I found based on your question: '{question}'"

    return jsonify({"answer": answer_text, "links": links})

PORT = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=PORT, debug=True)
