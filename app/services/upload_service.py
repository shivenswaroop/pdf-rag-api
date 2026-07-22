"""Save uploaded PDF files to disk."""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(name: str | None) -> str:
    raw = name or "document.pdf"
    cleaned = re.sub(r"[^\w.\- ]+", "_", raw).strip() or "document.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    return cleaned[:200]


def save_pdf(file: UploadFile) -> tuple[str, str]:
    """Save the uploaded PDF and return (document_id, file_path)."""
    document_id = str(uuid.uuid4())
    filename = f"{document_id}_{_safe_filename(file.filename)}"
    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return document_id, str(file_path)
