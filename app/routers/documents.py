"""Document list, detail, delete, and vector-chunk inspect endpoints."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.services import document_registry
from app.services.vector_store import delete_by_document_id, list_chunks_by_document

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def list_documents():
    """List all uploaded documents."""
    return {"documents": document_registry.list_documents()}


@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get metadata for a single document."""
    doc = document_registry.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.get("/{document_id}/chunks")
async def get_document_chunks(document_id: str):
    """Inspect chunks stored in the vector database for a document."""
    doc = document_registry.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks = list_chunks_by_document(document_id)
    return {
        "document_id": document_id,
        "filename": doc.get("filename"),
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document from disk, registry, and the vector store."""
    doc = document_registry.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    deleted_chunks = delete_by_document_id(document_id)

    path = doc.get("path")
    if path:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Could not delete file %s: %s", path, exc)

    document_registry.remove_document(document_id)

    return {
        "message": "Document deleted.",
        "document_id": document_id,
        "deleted_chunks": deleted_chunks,
    }
