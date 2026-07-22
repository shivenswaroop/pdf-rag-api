"""ChromaDB persistence and retrieval for document chunks."""

from __future__ import annotations

import logging
import os
from typing import Any

import chromadb

from app.services.embedding_service import get_embeddings

logger = logging.getLogger(__name__)

# Distance threshold (Chroma default L2 or cosine). Higher = less similar.
# Override with RETRIEVAL_MAX_DISTANCE if needed for your collection metric.
MAX_DISTANCE = float(os.getenv("RETRIEVAL_MAX_DISTANCE", "1.2"))

client = chromadb.PersistentClient(path="vector_db")

collection = client.get_or_create_collection(name="documents")


def store_chunks(document_id: str, chunks: list[dict], embeddings) -> None:
    """Store chunks and embeddings in ChromaDB."""
    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        ids.append(f"{document_id}_chunk_{i}")
        documents.append(chunk["text"])
        metadatas.append({
            "document_id": document_id,
            "page": int(chunk["page"]),
            "chunk_index": i,
        })

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )
    logger.info("Stored %s chunks for document %s", len(ids), document_id)


def search_chunks(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search the most relevant chunks from ChromaDB.

    Returns a list of dicts with keys:
    id, text, page, document_id, distance
    """
    query_embedding = get_embeddings([query])[0]

    kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding.tolist()],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if document_id:
        kwargs["where"] = {"document_id": document_id}

    results = collection.query(**kwargs)

    hits: list[dict[str, Any]] = []
    if not results or not results.get("ids") or not results["ids"][0]:
        return hits

    ids = results["ids"][0]
    documents = results["documents"][0] if results.get("documents") else []
    metadatas = results["metadatas"][0] if results.get("metadatas") else []
    distances = results["distances"][0] if results.get("distances") else []

    for i, chunk_id in enumerate(ids):
        meta = metadatas[i] if i < len(metadatas) else {}
        hits.append({
            "id": chunk_id,
            "text": documents[i] if i < len(documents) else "",
            "page": int(meta.get("page", 0)),
            "document_id": meta.get("document_id", ""),
            "distance": float(distances[i]) if i < len(distances) else 1.0,
        })

    return hits


def filter_relevant(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only hits under the distance threshold."""
    return [h for h in hits if h.get("distance", 1.0) <= MAX_DISTANCE]


def delete_by_document_id(document_id: str) -> int:
    """Delete all chunks for a document. Returns count deleted (best-effort)."""
    existing = collection.get(where={"document_id": document_id})
    ids = existing.get("ids") or []
    if ids:
        collection.delete(ids=ids)
        logger.info("Deleted %s chunks for document %s", len(ids), document_id)
    return len(ids)


def list_chunks_by_document(document_id: str) -> list[dict[str, Any]]:
    """List all stored chunks for a document (vector DB inspect)."""
    result = collection.get(
        where={"document_id": document_id},
        include=["documents", "metadatas"],
    )
    chunks: list[dict[str, Any]] = []
    ids = result.get("ids") or []
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    for i, chunk_id in enumerate(ids):
        meta = metadatas[i] if i < len(metadatas) else {}
        text = documents[i] if i < len(documents) else ""
        chunks.append({
            "id": chunk_id,
            "page": int(meta.get("page", 0)),
            "chunk_index": int(meta.get("chunk_index", i)),
            "text": text,
        })

    chunks.sort(key=lambda c: (c["page"], c["chunk_index"]))
    return chunks
