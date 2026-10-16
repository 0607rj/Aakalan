"""Merge the findings of every document in a project (RFP, annexures, corrigenda, pre-bid
replies) into one extraction for the review screen and the estimate.

- Features: union of all documents, with every document's evidence kept.
- Numbers and choices: the RFP and annexures set a value (first stated wins); a corrigendum or
  pre-bid reply overrides it (latest wins). Every override is recorded in `changes`, so the
  user sees e.g. "Corrigendum changed deadline_months from 9 to 6".
- Unclear points: all kept.
"""

from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, Project
from app.services.extraction.tender import FoundValue, TenderExtraction

OVERRIDING_KINDS = frozenset({"corrigendum", "prebid_reply"})


class Change(BaseModel):
    field: str
    old_value: Any
    new_value: Any
    document: str
    kind: str


class DocumentInfo(BaseModel):
    id: str
    filename: str
    kind: str
    pages: int
    status: str
    reader: str | None


class ProjectExtraction(BaseModel):
    project_id: str
    documents: list[DocumentInfo]
    extraction: TenderExtraction | None
    changes: list[Change]


def merge_extractions(
    docs: list[tuple[Document, TenderExtraction]],
) -> tuple[TenderExtraction, list[Change]]:
    """`docs` in upload order. The first document provides name and summary."""
    first = docs[0][1]
    merged = first.model_copy(deep=True)
    merged.features, merged.choices, merged.numbers, merged.unclear_points = [], {}, {}, []
    merged.dropped_findings = 0
    readers = {ex.reader for _, ex in docs}
    merged.reader = "ai" if readers == {"ai"} else ("basic" if readers == {"basic"} else "mixed")
    changes: list[Change] = []
    features: dict[str, Any] = {}

    def apply(target: dict[str, FoundValue], key: str, value: FoundValue, doc: Document) -> None:
        current = target.get(key)
        if current is None:
            target[key] = value
        elif doc.kind in OVERRIDING_KINDS and current.value != value.value:
            changes.append(
                Change(
                    field=key,
                    old_value=current.value,
                    new_value=value.value,
                    document=doc.filename,
                    kind=doc.kind,
                )
            )
            target[key] = value

    for doc, ex in docs:
        for f in ex.features:
            if f.key in features:
                features[f.key].evidence.extend(f.evidence)
            else:
                features[f.key] = f.model_copy(deep=True)
        for key, value in ex.choices.items():
            apply(merged.choices, key, value, doc)
        for key, value in ex.numbers.items():
            apply(merged.numbers, key, value, doc)
        merged.unclear_points.extend(ex.unclear_points)
        merged.dropped_findings += ex.dropped_findings
    merged.features = list(features.values())
    return merged, changes


def project_documents(db: Session, project: Project) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.project_id == project.id, Document.org_id == project.org_id)
            .order_by(Document.created_at)
        )
    )


def project_extraction(db: Session, project: Project) -> ProjectExtraction:
    docs = project_documents(db, project)
    readable = [(d, TenderExtraction.model_validate(d.extraction)) for d in docs if d.extraction]
    merged, changes = merge_extractions(readable) if readable else (None, [])
    return ProjectExtraction(
        project_id=project.id,
        documents=[
            DocumentInfo(
                id=d.id,
                filename=d.filename,
                kind=d.kind,
                pages=d.pages,
                status=d.parse_status,
                reader=(d.extraction or {}).get("reader"),
            )
            for d in docs
        ],
        extraction=merged,
        changes=changes,
    )
