import chromadb


def main():
    client = chromadb.PersistentClient(
        path="chroma_db"
    )

    collection = client.get_or_create_collection(
        name="chat_memory"
    )

    print("\nCHROMADB MEMORY")
    print("-------------------------")
    print(f"Collection: {collection.name}")
    print(f"Total memories: {collection.count()}")

    results = collection.get(
        include=[
            "documents",
            "metadatas",
        ]
    )

    records = []

    for memory_id, document, metadata in zip(
        results.get("ids", []),
        results.get("documents", []),
        results.get("metadatas", []),
    ):
        records.append(
            {
                "id": memory_id,
                "document": document,
                "question": metadata.get("question", ""),
                "answer": metadata.get("answer", ""),
                "timestamp": metadata.get("timestamp", ""),
            }
        )

    records.sort(
        key=lambda record: record["timestamp"],
        reverse=True,
    )

    print("\nRECENT MEMORIES")
    print("-------------------------")

    for index, record in enumerate(records[:20], start=1):
        answer = record["answer"] or "[No answer stored]"

        if len(answer) > 500:
            answer = answer[:500] + "... [truncated]"

        print(f"\nMemory #{index}")
        print(f"ID: {record['id']}")
        print(f"Question: {record['question']}")
        print(f"Answer: {answer}")
        print(f"Timestamp: {record['timestamp']}")


if __name__ == "__main__":
    main()
