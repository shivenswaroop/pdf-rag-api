"""Persistent JSON registry of uploaded documents."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path("storage/documents.json")
_lock = threading.Lock()


def _ensure_registry() -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.write_text("[]", encoding="utf-8")


def _read() -> list[dict[str, Any]]:
    _ensure_registry()
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read document registry: %s", exc)
    return []


def _write(documents: list[dict[str, Any]]) -> None:
    _ensure_registry()
    REGISTRY_PATH.write_text(
        json.dumps(documents, indent=2),
        encoding="utf-8",
    )


def list_documents() -> list[dict[str, Any]]:
    with _lock:
        docs = _read()
    return sorted(docs, key=lambda d: d.get("uploaded_at", ""), reverse=True)


def get_document(document_id: str) -> dict[str, Any] | None:
    with _lock:
        for doc in _read():
            if doc.get("document_id") == document_id:
                return doc
    return None


def add_document(
    document_id: str,
    filename: str,
    path: str,
    page_count: int,
    chunk_count: int,
) -> dict[str, Any]:
    record = {
        "document_id": document_id,
        "filename": filename,
        "path": path,
        "page_count": page_count,
        "chunk_count": chunk_count,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        docs = _read()
        docs.append(record)
        _write(docs)
    return record


def remove_document(document_id: str) -> dict[str, Any] | None:
    with _lock:
        docs = _read()
        remaining = []
        removed = None
        for doc in docs:
            if doc.get("document_id") == document_id:
                removed = doc
            else:
                remaining.append(doc)
        if removed is not None:
            _write(remaining)
        return removed
