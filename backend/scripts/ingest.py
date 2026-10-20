"""
ingest.py - build the ChromaDB knowledge base from slide-based markdown files.

Run from the rag-project folder (script can be in the root or in scripts/):
    pip install chromadb sentence-transformers
    python ingest.py            or    python scripts\\ingest.py

Expects:  data/lec1.md   (and later data/lec2.md, ...)
Creates:  chroma_db/     (persistent vector store)

One chunk per slide. Each chunk carries lecture_id, module_id, slide_number and
topic as metadata, so retrieval can be filtered by completed lectures and the
chatbot can show which slide an answer came from.
"""
import re
import sys
from pathlib import Path

# Works whether this file sits in the project root or in a scripts/ subfolder.
_HERE = Path(__file__).resolve().parent
ROOT = _HERE if (_HERE / "data").exists() else _HERE.parent
DATA_DIR = ROOT / "data"
DB_DIR = str(ROOT / "chroma_db")
COLLECTION = "course_chunks"

# FR-13: the SAME model must be used here and when embedding student queries.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def parse_front_matter(text):
    """Read the simple key: value header between the first two '---' lines."""
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.split("#")[0].strip()  # drop trailing comments
        text = text[m.end():]
    return meta, text


def parse_slides(path):
    """Return a list of chunks (dicts) for one markdown file."""
    raw = Path(path).read_text(encoding="utf-8")
    meta, body = parse_front_matter(raw)
    lecture_id = meta.get("lecture_id") or Path(path).stem
    module_id = meta.get("module_id", "unknown")

    chunks = []
    # split on "## Slide N" headings
    for match in re.finditer(r"^## Slide (\d+)[ \t]*\n(.*?)(?=^## Slide \d+[ \t]*$|\Z)", body, flags=re.S | re.M):
        number = int(match.group(1))
        content = match.group(2).strip()
        if not content:
            continue
        topic = content.splitlines()[0].strip()  # first line under the heading is the slide title
        text = f"Lecture: {lecture_id}, Slide {number}\n{content}"  # content already starts with the topic
        chunks.append({
            "id": f"{lecture_id}-slide-{number}",
            "text": text,
            "metadata": {
                "lecture_id": lecture_id,
                "module_id": module_id,
                "slide_number": number,
                "topic": topic,
                "source_file": Path(path).name,
                # True if the slide contains code/text added to complete or fix the original
                "has_reconstructed": bool(re.search(
                    r"\[(?:reconstructed|corrected|completed|unclear)\s*:", content, flags=re.IGNORECASE)),
                # True if the slide carries a note that it reflects older Java versions/terminology
                "has_lecture_note": bool(re.search(r"\[lecture note\s*:", content, flags=re.IGNORECASE)),
            },
        })
    return chunks


def main():
    import chromadb
    from chromadb.utils import embedding_functions

    files = sorted(DATA_DIR.glob("*.md"))
    if not files:
        sys.exit(f"No .md files found in {DATA_DIR.resolve()}")

    embed = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=embed,
        metadata={"embedding_model": EMBEDDING_MODEL},
    )

    total = 0
    for f in files:
        chunks = parse_slides(f)
        if not chunks:
            print(f"WARNING: no slides found in {f.name}")
            continue
        # remove chunks of this file that no longer exist (slide deleted/renumbered)
        new_ids = {c["id"] for c in chunks}
        old_ids = set(collection.get(where={"source_file": f.name}, include=[])["ids"])
        stale = sorted(old_ids - new_ids)
        if stale:
            collection.delete(ids=stale)
            print(f"{f.name}: removed {len(stale)} stale chunks")
        # upsert makes re-running safe (no duplicates, updates changed slides)
        collection.upsert(
            ids=[c["id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
        )
        print(f"{f.name}: {len(chunks)} chunks stored")
        total += len(chunks)

    print(f"Done. Collection '{COLLECTION}' now holds {collection.count()} chunks ({total} processed).")


if __name__ == "__main__":
    main()
