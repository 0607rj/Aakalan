"""Upload a tender document: store it, parse it, and (if an AI key is configured) extract
cited findings for the quick-estimate form. Each upload starts a draft project."""

import hashlib
import logging
import re
from typing import Any
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.tenancy import get_owned, scoped
from app.llm.client import LLMClient, LLMNotConfiguredError, LLMRefusedError, get_llm_client
from app.models import Document, Project, User
from app.services.documents.parsing import SCANNED_NEEDS_AI, DocumentError, parse_document
from app.services.extraction.basic_reader import basic_read
from app.services.extraction.tender import (
    BASIC_READER_VERSION,
    PROMPT_VERSION,
    ai_read,
    verify_findings,
)
from app.services.quick.config import quick_config

log = logging.getLogger(__name__)
BYTES_PER_MB = 1024 * 1024
# Later kinds override earlier ones when merged (a corrigendum changes the RFP).
DOCUMENT_KINDS = ("rfp", "annexure", "corrigendum", "prebid_reply")


def _safe_name(filename: str) -> str:
    name = Path(filename or "document").name
    return re.sub(r"[^A-Za-z0-9._ -]", "_", name)[:200] or "document"


def upload_document(
    db: Session,
    user: User,
    filename: str,
    data: bytes,
    *,
    project_id: str | None = None,
    kind: str = "rfp",
) -> Document:
    """Start a new draft project, or add an annexure / corrigendum / pre-bid reply to one."""
    settings = get_settings()
    if len(data) > settings.upload_max_mb * BYTES_PER_MB:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, f"File is larger than {settings.upload_max_mb} MB."
        )
    safe = _safe_name(filename)
    try:
        parsed = parse_document(safe, data)
    except DocumentError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    llm: LLMClient | None
    try:
        llm = get_llm_client()
    except LLMNotConfiguredError:
        llm = None
    if parsed.scanned and llm is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, SCANNED_NEEDS_AI)
    if parsed.char_count > settings.document_max_chars:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This document is too long to read in one go. "
            "Upload the main requirement document only.",
        )

    if kind not in DOCUMENT_KINDS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown document kind {kind!r}"
        )
    first_document = project_id is None
    if project_id is not None:
        project = get_owned(db, Project, project_id, user.org_id)
    else:
        project = Project(
            org_id=user.org_id,
            name=Path(safe).stem[:300],
            buyer_type="govt",
            domain="quick_estimate",
            status="draft",
            description=f"Created from uploaded document {safe}.",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
    doc = Document(
        org_id=user.org_id,
        project_id=project.id,
        filename=safe,
        kind=kind,
        file_type=parsed.kind,
        pages=len(parsed.pages),
        approximate_pages=parsed.approximate_pages,
        sha256=hashlib.sha256(data).hexdigest(),
        storage_path="",
        parse_status="parsed",
        page_texts=[{"page": p.number, "text": p.text} for p in parsed.pages],
        uploaded_by=user.id,
    )
    db.add(doc)
    db.flush()
    folder = settings.data_dir / "uploads" / user.org_id / project.id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{doc.id}.{parsed.kind}"
    path.write_bytes(data)
    doc.storage_path = str(path)

    cfg = quick_config()
    earlier = _earlier_reading(db, user.org_id, doc.sha256, settings.llm_model)
    if llm is not None and earlier is not None:
        # The same file read before by the same reader and model: reuse that reading, so one
        # file always gives the same findings (and the same price), and nothing is paid twice.
        doc.extraction = _renamed(earlier.extraction, earlier.filename, safe)
        doc.llm_model = earlier.llm_model
        doc.llm_input_tokens = doc.llm_output_tokens = 0
        doc.parse_status = "extracted"
        if first_document:
            project.name = doc.extraction.get("project_name") or project.name
        db.commit()
        db.refresh(doc)
        return doc
    try:
        if llm is None:
            raise LLMNotConfiguredError("no AI key")
        result = ai_read(llm, cfg, parsed, pdf=data if parsed.scanned else None)
    except LLMNotConfiguredError:
        # No AI key: the basic keyword reader still pre-fills the form, with citations.
        raw, reader, version = basic_read(cfg, parsed), "basic", BASIC_READER_VERSION
    except LLMRefusedError as exc:
        raw, reader, version = None, "", ""
        doc.parse_status, doc.error = "failed", str(exc)
    except Exception as exc:  # network / API errors: keep the upload, let the user continue
        log.exception("tender extraction failed")
        raw, reader, version = None, "", ""
        doc.parse_status = "failed"
        doc.error = f"The AI could not read the document ({type(exc).__name__}). Please try again."
    else:
        raw, reader, version = result.output, "ai", PROMPT_VERSION
        doc.llm_model = result.model
        doc.llm_input_tokens, doc.llm_output_tokens = result.input_tokens, result.output_tokens
    if raw is not None:
        extraction = verify_findings(
            cfg, parsed, raw, reader=reader, version=version, document=safe
        )
        doc.extraction = extraction.model_dump(mode="json")
        doc.parse_status = "extracted"
        if first_document:
            project.name = extraction.project_name
    db.commit()
    db.refresh(doc)
    return doc


def _earlier_reading(db: Session, org_id: str, sha256: str, model: str) -> Document | None:
    """The newest AI reading of the same file in this organisation, by the current prompt
    version and model; None if there is none (then the file is read fresh)."""
    rows = db.scalars(
        scoped(Document, org_id)
        .where(
            Document.sha256 == sha256,
            Document.parse_status == "extracted",
            Document.llm_model == model,
        )
        .order_by(Document.created_at.desc())
    )
    for row in rows:
        ex = row.extraction or {}
        if ex.get("reader") == "ai" and ex.get("prompt_version") == PROMPT_VERSION:
            return row
    return None


def _renamed(value: Any, old: str, new: str) -> Any:
    """A stored reading with its quotes pointing at the new upload's file name."""
    if isinstance(value, dict):
        return {
            k: (new if k == "document" and v == old else _renamed(v, old, new))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_renamed(v, old, new) for v in value]
    return value
