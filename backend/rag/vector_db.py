"""Vector database: document chunking, embedding, and ChromaDB storage."""
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

import chromadb
import dashscope
from chromadb.config import Settings as ChromaSettings
from langchain_text_splitters import MarkdownHeaderTextSplitter

from app.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-v4"
COLLECTION_NAME = "travel_guides"
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_data")
GUIDES_DIR = Path(__file__).parent.parent / "data" / "guides"

_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        chroma_path = os.path.abspath(CHROMA_DIR)
        os.makedirs(chroma_path, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info("ChromaDB client initialized at %s", chroma_path)
    return _client


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection '%s' ready", COLLECTION_NAME)
    return _collection


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using DashScope."""
    if not texts:
        return []
    dashscope.api_key = settings.DASHSCOPE_API_KEY
    # DashScope API accepts up to 25 texts per batch
    all_embeddings = []
    batch_size = 20
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = dashscope.TextEmbedding.call(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Embedding API error: code={resp.status_code}, message={resp.message}")
        embeddings = [item["embedding"] for item in resp.output["embeddings"]]
        all_embeddings.extend(embeddings)
        logger.info("Embedded batch %d/%d: %d texts", i // batch_size + 1, (len(texts) + batch_size - 1) // batch_size, len(batch))
    return all_embeddings


def add_documents(guide_dir: Optional[Path] = None) -> int:
    """Read markdown guides, chunk by ## headers, embed, and store in ChromaDB.

    Returns the number of chunks added.
    """
    if guide_dir is None:
        guide_dir = GUIDES_DIR
    if not guide_dir.exists():
        logger.warning("Guide directory not found: %s", guide_dir)
        return 0

    collection = _get_collection()
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "section")]
    )

    all_ids = []
    all_docs = []
    all_metadatas = []

    for md_file in guide_dir.glob("*.md"):
        city = md_file.stem
        text = md_file.read_text(encoding="utf-8")
        chunks = splitter.split_text(text)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{city}_chunk_{i:03d}"
            content = chunk.page_content.strip()
            if not content or len(content) < 30:
                continue
            all_ids.append(chunk_id)
            all_docs.append(content)
            all_metadatas.append({
                "city": city,
                "source_file": md_file.name,
                "chunk_index": i,
                "section": chunk.metadata.get("section", ""),
            })

    if not all_docs:
        logger.warning("No chunks generated from guides")
        return 0

    logger.info("Embedding %d chunks from %d guides...", len(all_docs), len(list(guide_dir.glob("*.md"))))
    embeddings = _embed_texts(all_docs)

    # Upsert in batches
    batch_size = 100
    for i in range(0, len(all_ids), batch_size):
        end = min(i + batch_size, len(all_ids))
        collection.upsert(
            ids=all_ids[i:end],
            embeddings=embeddings[i:end],
            documents=all_docs[i:end],
            metadatas=all_metadatas[i:end],
        )
    logger.info("Added %d chunks to ChromaDB", len(all_ids))
    # Store file hash for change detection
    try:
        collection.modify(metadata={"file_hash": _get_file_hash()})
    except Exception:
        pass
    return len(all_ids)


def _get_file_hash() -> str:
    """Generate a hash of guide file names for change detection."""
    if not GUIDES_DIR.exists():
        return ""
    files = sorted(md_file.name for md_file in GUIDES_DIR.glob("*.md"))
    return hashlib.md5("|".join(files).encode()).hexdigest()


def _ensure_indexed() -> None:
    """Auto-index guides if the collection is empty or new files were added."""
    collection = _get_collection()
    try:
        current_hash = _get_file_hash()
        if not current_hash:
            return
        stored_hash = collection.metadata.get("file_hash", "")
        if collection.count() == 0 or stored_hash != current_hash:
            logger.info("ChromaDB needs indexing (count=%d, hash_changed=%s)",
                        collection.count(), stored_hash != current_hash)
            add_documents()
    except Exception as e:
        logger.warning("Failed to check/auto-index ChromaDB: %s", e)


def search(query: str, city: str, top_k: int = 10) -> list[dict]:
    """Search for relevant chunks by query and city filter.

    Returns a list of {id, content, metadata, score}.
    """
    _ensure_indexed()
    collection = _get_collection()
    try:
        count = collection.count()
        if count == 0:
            logger.warning("ChromaDB collection is empty")
            return []
    except Exception:
        pass

    query_embeddings = _embed_texts([query])
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=min(top_k, 20),
        where={"city": city},
        include=["documents", "metadatas", "distances"],
    )

    if not results["ids"] or not results["ids"][0]:
        logger.info("No search results for query='%s', city='%s'", query, city)
        return []

    output = []
    for i, chunk_id in enumerate(results["ids"][0]):
        dist = results["distances"][0][i] if results["distances"] else 0
        # Cosine distance to similarity (cosine distance in [0, 2])
        similarity = 1.0 - (dist / 2.0)
        output.append({
            "id": chunk_id,
            "content": results["documents"][0][i] if results["documents"] else "",
            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            "score": round(similarity, 4),
        })

    logger.info("Vector search: %d results for query='%s', city='%s'", len(output), query[:50], city)
    return output
