"""PDF upload endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, UploadFile

from app.services.ingest_service import ingest_pdf

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and index a single PDF document."""
    return ingest_pdf(file)


@router.post("/bulk/")
async def upload_bulk(files: list[UploadFile] = File(...)):
    """Upload and index multiple PDF documents."""
    results = []
    for file in files:
        try:
            result = ingest_pdf(file)
            results.append({"ok": True, **result})
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            logger.warning("Bulk upload failed for %s: %s", file.filename, detail)
            results.append({
                "ok": False,
                "filename": file.filename,
                "error": detail,
            })
    succeeded = sum(1 for r in results if r.get("ok"))
    return {
        "message": f"Processed {len(results)} file(s); {succeeded} succeeded.",
        "results": results,
    }
