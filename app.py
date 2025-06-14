from flask import Flask, request, jsonify
import base64, os, json
from sentence_transformers import SentenceTransformer, util

app = Flask(__name__)

# Load saved posts
with open("discourse_posts.json") as f:
    posts = json.load(f)

# Prepare sentences for embedding
titles = [p['title'] for p in posts]
urls = [f"https://discourse.onlinedegree.iitm.ac.in/t/{p['id']}" for p in posts]

model = SentenceTransformer('all-MiniLM-L6-v2')
title_embeddings = model.encode(titles, convert_to_tensor=True)

@app.route("/api/", methods=["POST"])
def answer():
    data = request.get_json()
    question = data.get("question")
    image_b64 = data.get("image", None)

    if not question:
        return jsonify({"error": "Question is required"}), 400

    # Embed and find best matches
    q_embed = model.encode(question, convert_to_tensor=True)
    hits = util.semantic_search(q_embed, title_embeddings, top_k=2)[0]

    links = []
    for h in hits:
        idx = h["corpus_id"]
        links.append({
            "url": urls[idx],
            "text": titles[idx]
        })

    answer_text = f"Here's what I found based on your question: '{question}'"

    return jsonify({
        "answer": answer_text,
        "links": links
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
