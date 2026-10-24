"""Tender document upload and its AI extraction (for the quick-estimate form)."""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession, EditorUser
from app.core.tenancy import get_owned
from app.models import Document, Project
from app.services.documents.service import upload_document
from app.services.extraction.merge import (
    ProjectExtraction,
    project_extraction,
)
from app.services.extraction.prebid import PrebidQuery, prebid_queries
from app.services.extraction.tender import TenderExtraction
from app.services.quick.config import quick_config
from app.services.quick.prefill import ReviewPrefill, review_prefill

router = APIRouter(tags=["documents"])


class DocumentOut(BaseModel):
    id: str
    project_id: str
    project_name: str
    filename: str
    file_type: str
    pages: int
    approximate_pages: bool
    status: str
    error: str | None
    # the project's reading, all its documents merged with the code checks applied: the one
    # the price uses, so the review form pre-fills the same answers (OPEN_QUESTIONS 159)
    extraction: TenderExtraction | None
    llm_model: str | None
    llm_input_tokens: int
    llm_output_tokens: int


def _out(db: Session, doc: Document, project: Project) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        project_id=doc.project_id,
        project_name=project.name,
        filename=doc.filename,
        file_type=doc.file_type,
        pages=doc.pages,
        approximate_pages=doc.approximate_pages,
        status=doc.parse_status,
        error=doc.error,
        extraction=project_extraction(db, project).extraction if doc.extraction else None,
        llm_model=doc.llm_model,
        llm_input_tokens=doc.llm_input_tokens,
        llm_output_tokens=doc.llm_output_tokens,
    )


@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload(
    db: DbSession,
    user: EditorUser,
    file: Annotated[UploadFile, File()],
    project_id: Annotated[str | None, Form()] = None,
    kind: Annotated[str, Form()] = "rfp",
) -> DocumentOut:
    """Upload the RFP (starts a draft project) or add an annexure / corrigendum / pre-bid reply
    to an existing one via `project_id` + `kind`. Sync on purpose: parsing and the AI call run
    in the threadpool, not the event loop."""
    data = file.file.read()
    doc = upload_document(
        db, user, file.filename or "document", data, project_id=project_id, kind=kind
    )
    return _out(db, doc, get_owned(db, Project, doc.project_id, user.org_id))


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: DbSession, user: CurrentUser) -> DocumentOut:
    doc = get_owned(db, Document, document_id, user.org_id)
    return _out(db, doc, get_owned(db, Project, doc.project_id, user.org_id))


@router.get("/documents/{document_id}/prebid-queries", response_model=list[PrebidQuery])
def get_prebid_queries(document_id: str, db: DbSession, user: CurrentUser) -> list[PrebidQuery]:
    """Draft pre-bid queries: vague clauses plus key facts the tender leaves out."""
    doc = get_owned(db, Document, document_id, user.org_id)
    merged = project_extraction(db, get_owned(db, Project, doc.project_id, user.org_id)).extraction
    return prebid_queries(quick_config(), merged) if merged else []


@router.get("/documents/{document_id}/form", response_model=ReviewPrefill)
def get_review_form(
    document_id: str, db: DbSession, user: CurrentUser, country: str = "india"
) -> ReviewPrefill:
    """The review form's starting state for the project's reading, and the request it sends
    when everything is accepted (services/quick/prefill: the production-path back-test prices
    that same request)."""
    doc = get_owned(db, Document, document_id, user.org_id)
    project = get_owned(db, Project, doc.project_id, user.org_id)
    merged = project_extraction(db, project).extraction if doc.extraction else None
    if merged is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This document has not been read.")
    form = review_prefill(quick_config(), merged, country)
    request = form.request.model_copy(update={"document_id": doc.id})
    return form.model_copy(update={"request": request})


@router.get("/projects/{project_id}/extraction", response_model=ProjectExtraction)
def get_project_extraction(project_id: str, db: DbSession, user: CurrentUser) -> ProjectExtraction:
    """Findings of all the project's documents merged; corrigenda override the RFP."""
    return project_extraction(db, get_owned(db, Project, project_id, user.org_id))
