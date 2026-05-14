import uuid
from datetime import datetime
import chromadb
from sentence_transformers import SentenceTransformer
from app.agent.config import CHROMA_DB_PATH


# ChromaDB client
client = chromadb.PersistentClient(
    path=CHROMA_DB_PATH
)

# Collection
collection = client.get_or_create_collection(
    name="chat_memory",
    metadata={"hnsw:space": "cosine"}
)

# Embedding model
embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

def save_memory(question: str, answer: str):

    # Create embedding ONLY from question
    embedding = embedding_model.encode(
        question
    ).tolist()

    # Store in ChromaDB
    collection.add(
        documents=[question],
        embeddings=[embedding],
        ids=[str(uuid.uuid4())],
        metadatas=[
            {
                "question": question,
                "answer": answer,
                "timestamp": datetime.now().isoformat()
            }
        ]
    )

def retrieve_memory(
    query: str,
    top_k: int = 3,
    similarity_threshold: float = 0.1
):

    # Empty DB check
    if collection.count() == 0:
        return []

    # Query embedding
    query_embedding = embedding_model.encode(
        query
    ).tolist()

    # Search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["metadatas", "distances"]
    )

    memories = []

    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for meta, distance in zip(metadatas, distances):

        similarity = 1 - distance

        print(meta["question"])
        print(similarity)
        print("-----------")

        # Filter low similarity memories
        if similarity < similarity_threshold:
            continue

        memories.append(
            {
                "question": meta["question"],
                "answer": meta["answer"],
                "similarity": round(similarity, 2),
                "timestamp": meta["timestamp"]
            }
        )

    return memories


def retrieve_recent_memory(limit: int = 5):

    if collection.count() == 0:
        return []

    results = collection.get(
        include=["metadatas"]
    )

    metadatas = results.get("metadatas", [])

    sorted_metadatas = sorted(
        metadatas,
        key=lambda meta: meta.get("timestamp", ""),
        reverse=True,
    )

    return [
        {
            "question": meta["question"],
            "answer": meta["answer"],
            "timestamp": meta["timestamp"],
        }
        for meta in sorted_metadatas[:limit]
    ]

