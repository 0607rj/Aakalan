"""Merge the findings of every document in a project (RFP, annexures, corrigenda, pre-bid
replies) into one extraction for the review screen and the estimate.

- Features: union of all documents, with every document's evidence kept.
- Numbers and choices: the RFP and annexures set a value (first stated wins); a corrigendum or
  pre-bid reply overrides it (latest wins). Every override is recorded in `changes`, so the
  user sees e.g. "Corrigendum changed deadline_months from 9 to 6".
- Unclear points: all kept. Not-priced topics: union. Payment terms: like a number.
"""

import re
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, Project
from app.services.extraction.client_provided import client_provides, find_client_provided
from app.services.extraction.coverage import find_uncovered, terms_page
from app.services.extraction.staffing import apply_staffing
from app.services.extraction.stated_counts import StatedCount, find_stated_counts
from app.services.extraction.support_terms import find_support_hours, find_support_staff
from app.services.extraction.tender import (
    FoundFeature,
    FoundValue,
    TenderExtraction,
    UnclearPoint,
    VerifiedEvidence,
)
from app.services.extraction.uptime_terms import find_uptime
from app.services.quick.config import quick_config
from app.services.quick.context import user_roles

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
    merged.uncovered, merged.uncovered_more = [], 0
    merged.project_domain = next((ex.project_domain for _, ex in docs if ex.project_domain), "")
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
    # the first file's "usually needed" list, less what any file (or the keyword net) found
    found = {f.key for f in merged.features}
    names = {o.name.strip().lower() for o in merged.other_features}
    merged.ready_made = next((ex.ready_made for _, ex in docs if ex.ready_made), None)
    merged.industry_suggestions_asked = any(ex.industry_suggestions_asked for _, ex in docs)
    merged.industry_suggestions = [
        s
        for s in next((ex.industry_suggestions for _, ex in docs if ex.industry_suggestions), [])
        if s.feature not in found and (s.feature or s.label.strip().lower() not in names)
    ]
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
    _uptime_terms(extraction, docs)
    apply_stated_counts(extraction, docs)
    apply_staffing(quick_config(), extraction, docs)  # staff lines and rules (OPEN_QUESTIONS 162)
    _drop_unstated(extraction)
    _outside_scope(extraction, docs)
    _coverage(extraction, docs)
    _roles(extraction)
    _own_report(extraction, docs)
    return extraction


# A sentence saying the document does not give something, or asking for it, answers nothing:
# "The requirement document does not state the helpdesk support hours", "Kindly confirm the
# O&M period", "Is migration required?" (OPEN_QUESTIONS 218). Wording, not tunable numbers.
UNSTATED = re.compile(
    r"\b(?:does|do|did)\s+not\s+(?:state|specify|mention|say|indicate|provide|define)"
    r"|\bnot\s+(?:been\s+|yet\s+)?(?:stated|specified|mentioned|provided|defined|given|indicated)\b"
    r"|\b(?:kindly|please)\s+(?:confirm|specify|clarify|provide|state|indicate|advise)"
    r"|\bis\s+silent\s+(?:on|about)\b",
    re.IGNORECASE,
)


def unstated(quote: str) -> bool:
    """True for a sentence that says something is not stated, asks for it, or is a question."""
    text = quote.strip()
    return text.endswith("?") or UNSTATED.search(text) is not None


# An e-mail address or a phone number (ten digits or more): contact details, not something to
# build or run. "Register with a mobile number" is a feature, so the words alone never count.
CONTACT = re.compile(
    r"[\w.+-]+@[\w-]+\.[a-z]{2,}|\+?\b\d[\d -]{8,}\d\b",
    re.IGNORECASE,
)


def about_tendering(quote: str) -> bool:
    """True for a sentence about the tendering process itself (quick config `tender_process`:
    the portal, bidder registration, bid submission) or giving contact details: the buyer's or
    the portal's helpdesk for bidders is not a helpdesk to provide (OPEN_QUESTIONS 219)."""
    rules = quick_config().tender_process
    text = " ".join(quote.lower().split())
    if CONTACT.search(text):
        return True
    return rules is not None and any(w in text for w in rules.words)


def _drop_unstated(merged: TenderExtraction) -> None:
    """An answer or number whose every quote only says the document does not state it (or asks
    for it) is dropped, so the question keeps its usual answer (OPEN_QUESTIONS 218); so is an
    answer whose every quote is about the tendering process (219; a number such as the EMD may
    come from there). It counts as a dropped finding; the pre-bid query, if any, stays."""
    for key in [k for k, v in merged.choices.items() if v.evidence]:
        quotes = [ev.quote for ev in merged.choices[key].evidence]
        if all(unstated(q) or about_tendering(q) for q in quotes):
            del merged.choices[key]
            merged.dropped_findings += 1
    for key in [k for k, v in merged.numbers.items() if v.evidence]:
        if all(unstated(ev.quote) for ev in merged.numbers[key].evidence):
            del merged.numbers[key]
            merged.dropped_findings += 1


def _roles(merged: TenderExtraction) -> None:
    """The user roles named in the reading's user stories, shown only (OPEN_QUESTIONS 205)."""
    rules = quick_config().project_context
    if rules is None:
        return
    stories = [s for f in merged.features for s in f.stories]
    stories += [s for o in merged.other_features for s in o.stories]
    merged.user_roles = user_roles(stories, rules.max_roles)


def _own_report(merged: TenderExtraction, docs: list[Document]) -> None:
    """Flags a file that is one of our own estimate reports (its footer, quick config
    `own_report`) so the review screen can say to upload the requirement document instead
    (OPEN_QUESTIONS 220)."""
    rules = quick_config().own_report
    if rules is None:
        return
    merged.own_report = any(
        phrase in " ".join(text.lower().split())
        for doc in docs
        for _, text in _pages(doc)
        for phrase in rules.phrases
    )


def _outside_scope(merged: TenderExtraction, docs: list[Document]) -> None:
    """A feature or extra whose every quote sits on a page of contract or bid terms (the strict
    `coverage.terms_page`), is about the tendering process or says something is not stated is
    marked `outside_scope` and not ticked: offered with its page, never dropped, since tenders
    also ask for work in price tables and annexures (OPEN_QUESTIONS 220)."""
    rules = quick_config().coverage
    if rules is None:
        return
    terms = {
        (doc.filename, page)
        for doc in docs
        for page, text in _pages(doc)
        if terms_page(rules, text, strict=True)
    }
    single = docs[0].filename if len(docs) == 1 else ""

    def outside(evidence: list[VerifiedEvidence]) -> bool:
        return bool(evidence) and all(
            (ev.document or single, ev.page) in terms
            or about_tendering(ev.quote)
            or unstated(ev.quote)
            for ev in evidence
        )

    for feature in merged.features:
        if outside(feature.evidence):
            feature.outside_scope, feature.suggested = True, False
    for other in merged.other_features:
        other.outside_scope = outside(other.evidence)


def _pages(doc: Document) -> list[tuple[int, str]]:
    return [(int(p["page"]), str(p["text"])) for p in (doc.page_texts or [])]


def _coverage(merged: TenderExtraction, docs: list[Document]) -> None:
    """Requirement sentences no finding quotes, listed for the review (OPEN_QUESTIONS 204)."""
    cfg = quick_config().coverage
    if cfg is None:
        return
    pages = [(doc.filename, _pages(doc)) for doc in docs]
    merged.uncovered, merged.uncovered_more = find_uncovered(cfg, merged, pages)


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


def apply_stated_counts(
    merged: TenderExtraction, docs: list[Document] | list[tuple[str, list[tuple[int, str]]]]
) -> None:
    """Counts the documents state for what is built ("200 services", "integration with 20 State
    Systems") make that feature several modules at the rule's level, citing the line
    (services/extraction/stated_counts.py, OPEN_QUESTIONS 194). A count only raises the
    modules the reading found, never lowers them. After an AI reading a count only sizes a
    feature the AI found; it never adds one (OPEN_QUESTIONS 217). `docs`: documents, or (file
    name, pages)."""
    cfg = quick_config()
    rules = cfg.stated_counts
    if rules is None:
        return
    found: dict[str, StatedCount] = {}
    for doc in docs:
        if isinstance(doc, tuple):
            filename, pages = doc
        else:
            filename = doc.filename
            pages = [(int(p["page"]), str(p["text"])) for p in (doc.page_texts or [])]
        for key, hit in find_stated_counts(rules, pages, filename, cfg.sizing.max_units).items():
            if key not in found or hit.count > found[key].count:
                found[key] = hit
    features = {f.key: f for f in merged.features}
    for key, hit in found.items():
        feature = features.get(key)
        if feature is None and merged.reader == "ai":
            continue  # the AI read the document and did not ask for it (OPEN_QUESTIONS 217)
        if feature is None:
            feature = FoundFeature(key=key, label=cfg.feature(key).label, evidence=[])
            merged.features.append(feature)
        if hit.units <= feature.story_units:
            continue
        feature.story_units = hit.units
        feature.story_level = hit.level  # type: ignore[assignment]
        feature.suggested = True
        if hit.evidence not in feature.evidence:
            feature.evidence.append(hit.evidence)


def _uptime_terms(merged: TenderExtraction, docs: list[Document]) -> None:
    """The uptime the document asks for (an SLA's penalty threshold or a stated figure) answers
    the downtime question with the lowest option that meets it, citing the line; it wins over
    the reading's answer (services/extraction/uptime_terms.py, OPEN_QUESTIONS 219)."""
    cfg = quick_config()
    terms = cfg.uptime_terms
    question = cfg.questions.get("availability")
    if terms is None or question is None:
        return
    asked = None
    for doc in docs:
        pages = [(int(p["page"]), str(p["text"])) for p in (doc.page_texts or [])]
        found = find_uptime(terms, pages, doc.filename)
        if found is not None and (asked is None or found.percent > asked.percent):
            asked = found
    if asked is None:
        return
    by_uptime = sorted(
        (
            (Decimal(str(o.answers["uptime_sla"])), o)
            for o in question.options
            if "uptime_sla" in o.answers
        ),
        key=lambda pair: pair[0],
    )
    if not by_uptime:
        return
    option = next((o for up, o in by_uptime if up >= asked.percent), by_uptime[-1][1])
    merged.choices["availability"] = FoundValue(
        value=option.value, label=option.label, evidence=[asked.evidence]
    )


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
