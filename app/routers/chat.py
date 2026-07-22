"""Question-answering endpoint grounded in uploaded documents."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.chat_service import REFUSAL_MESSAGE, generate_answer
from app.services.document_registry import get_document, list_documents
from app.services.vector_store import filter_relevant, search_chunks

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    document_id: Optional[str] = None


@router.post("/")
async def ask_question(request: QueryRequest):
    """Answer a question using retrieved document context only."""
    if not list_documents():
        raise HTTPException(
            status_code=400,
            detail="No documents uploaded yet. Upload a PDF first.",
        )

    if request.document_id and not get_document(request.document_id):
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        hits = search_chunks(
            request.question,
            top_k=5,
            document_id=request.document_id,
        )
    except Exception as exc:
        logger.exception("Vector search failed")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {exc}",
        ) from exc

    relevant = filter_relevant(hits)

    if not relevant:
        return {
            "answer": REFUSAL_MESSAGE,
            "sources": [],
        }

    context = "\n\n".join(
        f"[page {h['page']}]\n{h['text']}" for h in relevant
    )

    try:
        answer = generate_answer(request.question, context)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM request failed: {exc}",
        ) from exc

    sources = []
    seen = set()
    for hit in relevant:
        key = (hit["document_id"], hit["page"], hit.get("id"))
        if key in seen:
            continue
        seen.add(key)
        doc = get_document(hit["document_id"]) if hit.get("document_id") else None
        sources.append({
            "page": hit["page"],
            "document_id": hit["document_id"],
            "filename": doc.get("filename") if doc else None,
            "text": hit["text"],
            "snippet": hit["text"],
        })

    return {
        "answer": answer,
        "sources": sources,
    }
