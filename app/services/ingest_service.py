"""Shared PDF ingest pipeline: save → extract → chunk → embed → store."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.services.chunk_service import chunk_text
from app.services.document_registry import add_document
from app.services.embedding_service import get_embeddings
from app.services.pdf_service import extract_text
from app.services.upload_service import save_pdf
from app.services.vector_store import store_chunks

logger = logging.getLogger(__name__)


def ingest_pdf(file: UploadFile) -> dict:
    """Process a single uploaded PDF and return its registry record + message."""
    if file.content_type and file.content_type not in (
        "application/pdf",
        "application/x-pdf",
    ):
        # Some browsers omit or mis-set content_type; also check extension.
        name = (file.filename or "").lower()
        if not name.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed.",
            )

    try:
        document_id, file_path = save_pdf(file)
        pages = extract_text(file_path)

        non_empty = [p for p in pages if (p.get("text") or "").strip()]
        if not non_empty:
            Path(file_path).unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail=(
                    "No extractable text found in this PDF. "
                    "Scanned/image-only PDFs without OCR are not supported."
                ),
            )

        chunks = chunk_text(pages)
        if not chunks:
            Path(file_path).unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail="Could not create text chunks from this PDF.",
            )

        texts = [chunk["text"] for chunk in chunks]
        embeddings = get_embeddings(texts)
        store_chunks(document_id, chunks, embeddings)

        record = add_document(
            document_id=document_id,
            filename=file.filename or "document.pdf",
            path=file_path,
            page_count=len(pages),
            chunk_count=len(chunks),
        )

        logger.info(
            "Ingested %s (%s pages, %s chunks)",
            record["filename"],
            record["page_count"],
            record["chunk_count"],
        )

        return {
            "document_id": document_id,
            "message": "PDF uploaded successfully.",
            "filename": record["filename"],
            "path": file_path,
            "page_count": record["page_count"],
            "chunk_count": record["chunk_count"],
            "uploaded_at": record["uploaded_at"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to ingest PDF %s", file.filename)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process PDF: {exc}",
        ) from exc
