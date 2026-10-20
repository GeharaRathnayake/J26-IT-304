
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

ROOT = Path(__file__).resolve().parent.parent
DB_DIR = str(ROOT / "chroma_db")
MODEL = "all-MiniLM-L6-v2"

embed = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=MODEL
)

client = chromadb.PersistentClient(path=DB_DIR)
collection = client.get_collection(
    name="course_chunks",
    embedding_function=embed
)

question = "What is a class in Java?"

results = collection.query(
    query_texts=[question],
    n_results=3
)

print(f"\nQuestion: {question}\n")
for doc, metadata, distance in zip(
    results["documents"][0],
    results["metadatas"][0],
    results["distances"][0]
):
    print(
        f"Slide {metadata['slide_number']} | "
        f"Topic: {metadata['topic']} | "
        f"Distance: {distance:.4f}"
    )
    print(doc[:500])
    print("-" * 50)

