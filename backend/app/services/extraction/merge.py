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
from app.services.extraction.client_provided import client_provides, find_client_provided
from app.services.extraction.staffing import apply_staffing
from app.services.extraction.support_terms import find_support_hours, find_support_staff
from app.services.extraction.tender import (
    FoundValue,
    TenderExtraction,
    UnclearPoint,
    VerifiedEvidence,
)
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
    merged.staff_lines, merged.chatbot_buyer_systems, merged.staffing = [], None, None
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
        # every file's staff statements: the code weighs them together (staffing.py)
        merged.staff_lines.extend(s.model_copy(deep=True) for s in ex.staff_lines)
        if ex.chatbot_buyer_systems is not None:
            if merged.chatbot_buyer_systems is None:
                merged.chatbot_buyer_systems = ex.chatbot_buyer_systems.model_copy(deep=True)
            else:
                merged.chatbot_buyer_systems.evidence.extend(ex.chatbot_buyer_systems.evidence)
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
    apply_code_checks(merged, [doc for doc, _ in docs])
    return merged, changes


def apply_code_checks(extraction: TenderExtraction, docs: list[Document]) -> TenderExtraction:
    """The answers found in code on the documents' page text rather than by the reader
    (answers from not-priced topics, items the client provides, support hours and staff, then
    the staff rules on the reading's staff lines),
    applied in place. The review form pre-fills from the same merged reading the price uses
    (GET /documents/{id}), so the two agree (OPEN_QUESTIONS 159)."""
    _answers_from_topics(extraction)
    _client_provided(extraction, docs)
    _support_terms(extraction, docs)
    apply_staffing(quick_config(), extraction, docs)  # staff lines and rules (OPEN_QUESTIONS 162)
    return extraction


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


def _client_provided(merged: TenderExtraction, docs: list[Document]) -> None:
    """A sentence saying the client provides hosting, the web address or the SSL certificate
    answers that question, citing the sentence (services/extraction/client_provided.py). It wins
    over the reading's answer: the document says who pays, whatever platform it names."""
    cfg = quick_config()
    if cfg.client_provided is None:
        return
    found: dict[str, tuple[str, VerifiedEvidence]] = {}
    for doc in docs:
        pages = [(int(p["page"]), str(p["text"])) for p in (doc.page_texts or [])]
        for key, hit in find_client_provided(cfg.client_provided, pages, doc.filename).items():
            found.setdefault(key, hit)
    # Hard check (OPEN_QUESTIONS 157): an answer whose own quote says the client provides the
    # item is the client's, whatever the reading answered, so no line cites a client-provided
    # clause and still charges for it.
    for answer in list(merged.choices.values()):
        for evidence in answer.evidence:
            for item in client_provides(cfg.client_provided, evidence.quote):
                found.setdefault(item.question, (item.value, evidence))
    for key, (value, evidence) in found.items():
        current = merged.choices.get(key)
        if current is not None and current.value == value:
            continue
        option = cfg.questions[key].option(value)
        merged.choices[key] = FoundValue(value=value, label=option.label, evidence=[evidence])


def _support_terms(merged: TenderExtraction, docs: list[Document]) -> None:
    """Support hours and dedicated support staff the document states answer the support
    hours question and the support_staff number, citing the sentence
    (services/extraction/support_terms.py); they win over the reading's answer. Round the
    clock with another sentence saying office hours becomes a pre-bid query, not a silent
    choice (OPEN_QUESTIONS 157)."""
    cfg = quick_config()
    terms = cfg.support_terms
    if terms is None:
        return
    hours = None
    staff = None
    for doc in docs:
        pages = [(int(p["page"]), str(p["text"])) for p in (doc.page_texts or [])]
        hours = hours or find_support_hours(terms, pages, doc.filename)
        staff = staff or find_support_staff(terms, pages, doc.filename)
    if hours is not None:
        option = cfg.questions["support_hours"].option(hours.value)
        merged.choices["support_hours"] = FoundValue(
            value=hours.value, label=option.label, evidence=[hours.evidence]
        )
        if hours.conflict is not None:
            merged.unclear_points.append(
                UnclearPoint(
                    topic="Support hours",
                    why=f"Round the clock on page {hours.evidence.page}, business or office "
                    f"hours on page {hours.conflict.page}.",
                    page=hours.conflict.page,
                    clause_ref=hours.conflict.clause_ref,
                    quote=hours.conflict.quote,
                    prebid_query=terms.conflict_query,
                    answer="support_hours",
                    document=hours.conflict.document,
                )
            )
    if staff is not None and cfg.support_role is not None:
        count, evidence = staff
        merged.numbers["support_staff"] = FoundValue(
            value=count, label=f"{count} dedicated support staff", evidence=[evidence]
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
