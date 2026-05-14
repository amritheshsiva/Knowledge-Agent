from app.memory.rag_memory import (
    save_memory,
    retrieve_memory
)


# Save memories
save_memory(
    "What frontend framework is used?",
    "The frontend uses Streamlit."
)

save_memory(
    "What backend framework is used?",
    "The backend uses FastAPI."
)

save_memory(
    "Which LLM provider is used?",
    "The project uses Groq."
)


# Retrieve memory
results = retrieve_memory(
    "What UI framework is used?"
)


print("\nRetrieved Memories:\n")

for memory in results:

    print(f"Question: {memory['question']}")
    print(f"Answer: {memory['answer']}")
    print(f"Similarity: {memory['similarity']}")
    print(f"Timestamp: {memory['timestamp']}")
    print("------------------------")