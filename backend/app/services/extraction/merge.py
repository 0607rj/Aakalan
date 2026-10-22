"""Merge the findings of every document in a project (RFP, annexures, corrigenda, pre-bid
replies) into one extraction for the review screen and the estimate.

- Features: union of all documents, with every document's evidence kept.
- Numbers and choices: the RFP and annexures set a value (first stated wins); a corrigendum or
  pre-bid reply overrides it (latest wins). Every override is recorded in `changes`, so the
  user sees e.g. "Corrigendum changed deadline_months from 9 to 6".
- Unclear points: all kept. Not-priced topics: union. Payment terms: like a number.
"""

from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, Project
from app.services.extraction.tender import FoundValue, TenderExtraction
from app.services.quick.config import quick_config

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
    merged.other_features, merged.not_priced, merged.payment_terms = [], [], None
    merged.scope, merged.scope_set_aside = [], []
    scope: dict[str, Any] = {}
    set_aside: dict[str, Any] = {}
    others: dict[str, Any] = {}
    not_priced: dict[str, Any] = {}
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
        for o in ex.other_features:
            if o.name.lower() in others:
                others[o.name.lower()].evidence.extend(o.evidence)
            else:
                others[o.name.lower()] = o.model_copy(deep=True)
        for key, value in ex.choices.items():
            apply(merged.choices, key, value, doc)
        for key, value in ex.numbers.items():
            apply(merged.numbers, key, value, doc)
        for sc in ex.scope:
            set_aside.pop(sc.key, None)
            if sc.key in scope:
                scope[sc.key].evidence.extend(sc.evidence)
                if sc.status == "explicit":
                    scope[sc.key].status = "explicit"
            else:
                scope[sc.key] = sc.model_copy(deep=True)
        for sc in ex.scope_set_aside:
            if doc.kind in OVERRIDING_KINDS:  # a corrigendum ruling it out wins
                scope.pop(sc.key, None)
            if sc.key not in scope:
                set_aside.setdefault(sc.key, sc.model_copy(deep=True))
        for n in ex.not_priced:
            if n.topic in not_priced:
                not_priced[n.topic].evidence.extend(n.evidence)
            else:
                not_priced[n.topic] = n.model_copy(deep=True)
        if ex.payment_terms is not None and (
            merged.payment_terms is None or doc.kind in OVERRIDING_KINDS
        ):
            merged.payment_terms = ex.payment_terms
        merged.unclear_points.extend(ex.unclear_points)
        merged.dropped_findings += ex.dropped_findings
    merged.features = list(features.values())
    merged.other_features = list(others.values())
    merged.scope = list(scope.values())
    merged.scope_set_aside = list(set_aside.values())
    # payment terms that were read are priced, so they are no longer "not priced"
    merged.not_priced = [
        n
        for n in not_priced.values()
        if not (n.topic == "payment_terms" and merged.payment_terms is not None)
    ]
    _answers_from_topics(merged)
    return merged, changes


YES = "yes"


def _answers_from_topics(merged: TenderExtraction) -> None:
    """A question with `from_not_priced` that the reading did not answer is answered "yes" by
    the quotes of that not-priced topic (e.g. a penalty clause), so the answer stays cited."""
    topics = {n.topic: n for n in merged.not_priced if n.evidence}
    for key, question in quick_config().questions.items():
        topic = topics.get(question.from_not_priced or "")
        if topic is None or key in merged.choices:
            continue
        option = question.option(YES)
        merged.choices[key] = FoundValue(
            value=option.value, label=option.label, evidence=list(topic.evidence)
        )


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
