"""Report data: one structure, read from the stored estimate, feeds both the PDF report and
the Excel BoQ, so exported numbers are exactly the numbers the API returns (brief M2)."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, Estimate, Project
from app.services.extraction.prebid import PrebidQuery, prebid_queries
from app.services.extraction.tender import TenderExtraction
from app.services.quick.config import quick_config
from app.services.quick.service import QuickSummary, summarise

MARGIN_BUCKET = "commercial.margin"
PAISE_PER_RUPEE = Decimal(100)


def rupees(paise: int) -> Decimal:
    return Decimal(paise) / PAISE_PER_RUPEE


def inr(paise: int | None, *, decimals: bool = True) -> str:
    """Indian digit grouping (12,34,56,789.00) with an 'Rs' prefix (portable PDF fonts lack ₹)."""
    if paise is None:
        return "-"
    negative = paise < 0
    whole, frac = divmod(abs(paise), 100)
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join([*groups, tail])
    text = f"Rs {digits}" + (f".{frac:02d}" if decimals else "")
    return f"-{text}" if negative else text


def crore(paise: int | None) -> str:
    """Headline figure, e.g. 'Rs 4.59 Cr' or 'Rs 85.3 L' (display only)."""
    if paise is None:
        return "-"
    value = rupees(paise)
    if value >= Decimal(10_000_000):
        return f"Rs {value / Decimal(10_000_000):.2f} Cr"
    if value >= Decimal(100_000):
        return f"Rs {value / Decimal(100_000):.1f} L"
    return inr(paise, decimals=False)


@dataclass
class ReportLine:
    number: int
    stage: str
    bucket: str
    bucket_name: str
    year: int
    label: str
    low_paise: int | None
    likely_paise: int | None
    high_paise: int | None
    redacted: bool
    formula_id: str
    formula: str
    requirements: list[dict[str, Any]]
    rate_items: list[dict[str, Any]]
    steps: list[dict[str, Any]]


@dataclass
class ReportData:
    project_name: str
    estimate: Estimate
    summary: QuickSummary
    result: dict[str, Any]
    lines: list[ReportLine]
    margin_visible: bool
    document_name: str | None = None
    prebid: list[PrebidQuery] = field(default_factory=list)


def build_report(
    db: Session, estimate: Estimate, project: Project, *, margin_visible: bool
) -> ReportData:
    cfg = quick_config()
    result: dict[str, Any] = estimate.result
    taxonomy = estimate.inputs_snapshot["taxonomy"]
    names = {b["key"]: b["name"] for b in taxonomy["buckets"]}
    lines = []
    for i, line in enumerate(estimate.lines, start=1):
        hide = line.bucket == MARGIN_BUCKET and not margin_visible
        trace = line.trace
        lines.append(
            ReportLine(
                number=i,
                stage=line.stage,
                bucket=line.bucket,
                bucket_name=names.get(line.bucket, line.bucket),
                year=line.year,
                label=line.label,
                low_paise=None if hide else line.low_paise,
                likely_paise=None if hide else line.likely_paise,
                high_paise=None if hide else line.high_paise,
                redacted=hide,
                formula_id=line.formula_id,
                formula=trace["formula"],
                requirements=[] if hide else trace["requirements"],
                rate_items=[] if hide else trace["rate_items"],
                steps=[] if hide else trace["steps"],
            )
        )
    doc = db.scalars(
        select(Document)
        .where(Document.project_id == project.id, Document.org_id == project.org_id)
        .order_by(Document.created_at.desc())
    ).first()
    prebid: list[PrebidQuery] = []
    if doc is not None and doc.extraction:
        prebid = prebid_queries(cfg, TenderExtraction.model_validate(doc.extraction))
    return ReportData(
        project_name=project.name,
        estimate=estimate,
        summary=summarise(estimate, project, cfg),
        result=result,
        lines=lines,
        margin_visible=margin_visible,
        document_name=doc.filename if doc else None,
        prebid=prebid,
    )
