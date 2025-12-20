import requests
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# -------------------------------
# 1. Load documents
# -------------------------------
with open("data/base.txt", "r", encoding="utf-8") as f:
    documents = f.read().split("\n")

documents = [d for d in documents if d.strip()]

# -------------------------------
# 2. Create embeddings
# -------------------------------
embedder = SentenceTransformer("all-MiniLM-L6-v2")
doc_embeddings = embedder.encode(documents, convert_to_numpy=True)

# -------------------------------
# 3. Build FAISS index
# -------------------------------
dim = doc_embeddings.shape[1]
index = faiss.IndexFlatL2(dim)
index.add(doc_embeddings)

# -------------------------------
# 4. Query loop
# -------------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"

print("Manual RAG ready. Type 'exit' to quit.\n")

while True:
    query = input("You: ")
    if query.lower() == "exit":
        break

    # Embed query
    query_embedding = embedder.encode([query], convert_to_numpy=True)

    # Retrieve top-k documents
    k = 3
    _, indices = index.search(query_embedding, k)
    retrieved_docs = [documents[i] for i in indices[0]]

    # Build prompt
    context = "\n".join(retrieved_docs)
    prompt = f"""
You are an assistant. Use the context below to answer the question.

Context:
{context}

Question:
{query}

Answer:
"""

    # Call LLM
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }
    )

    print("AI:", response.json()["response"])
