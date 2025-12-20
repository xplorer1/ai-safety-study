import requests
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# -------------------------------
# Load documents (shared memory)
# -------------------------------
with open("data/base.txt", "r", encoding="utf-8") as f:
    documents = [d for d in f.read().split("\n") if d.strip()]

embedder = SentenceTransformer("all-MiniLM-L6-v2")
doc_embeddings = embedder.encode(documents, convert_to_numpy=True)

dim = doc_embeddings.shape[1]
index = faiss.IndexFlatL2(dim)
index.add(doc_embeddings)

OLLAMA_URL = "http://localhost:11434/api/generate"

# -------------------------------
# Agent definitions
# -------------------------------
AGENTS = {
    "researcher": "You are a researcher. Explain concepts clearly and ground answers in the provided context.",
    "critic": "You are a critic. Question assumptions, point out limitations, and identify weaknesses.",
    "planner": "You are a planner. Suggest concrete next steps or actions based on the discussion."
}

def retrieve_context(query, k=3):
    q_emb = embedder.encode([query], convert_to_numpy=True)
    _, indices = index.search(q_emb, k)
    return "\n".join([documents[i] for i in indices[0]])

def run_agent(role, query, context):
    system_prompt = AGENTS[role]
    prompt = f"""
{system_prompt}

Context:
{context}

Question:
{query}

Answer:
"""
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "qwen2.5:3b",
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 150}
        }
    )
    return response.json()["response"]

# -------------------------------
# Village Orchestrator
# -------------------------------
print("AI Village ready. Type 'exit' to quit.\n")

while True:
    query = input("User: ")
    if query.lower() == "exit":
        break

    context = retrieve_context(query)

    print("\n--- Researcher ---")
    researcher_reply = run_agent("researcher", query, context)
    print(researcher_reply)

    print("\n--- Critic ---")
    critic_reply = run_agent("critic", query, context)
    print(critic_reply)

    print("\n--- Planner ---")
    planner_reply = run_agent("planner", query, context)
    print(planner_reply)

    print("\n" + "="*60 + "\n")
