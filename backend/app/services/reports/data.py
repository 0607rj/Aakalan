"""Report data: one structure, read from the stored estimate, feeds both the PDF report and
the Excel BoQ, so exported numbers are exactly the numbers the API returns (brief M2)."""

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
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


SYMBOLS = {"USD": "$"}
MILLION = Decimal(1_000_000)
THOUSAND = Decimal(1_000)


def fmt_money(minor: int | None, currency: str, *, decimals: bool = True) -> str:
    """Display an amount in minor units: Indian style for INR, Western grouping otherwise."""
    if currency == "INR":
        return inr(minor, decimals=decimals)
    if minor is None:
        return "-"
    symbol = SYMBOLS.get(currency, f"{currency} ")
    value = rupees(minor)  # minor units / 100 for both paise and cents
    return f"{symbol}{value:,.2f}" if decimals else f"{symbol}{value:,.0f}"


def fmt_headline(minor: int | None, currency: str) -> str:
    """Headline figure: 'Rs 4.59 Cr' / 'Rs 85.3 L' for INR, '$1.23 M' / '$450 K' otherwise."""
    if currency == "INR":
        return crore(minor)
    if minor is None:
        return "-"
    value = rupees(minor)
    symbol = SYMBOLS.get(currency, f"{currency} ")
    if value >= MILLION:
        return f"{symbol}{value / MILLION:.2f} M"
    if value >= THOUSAND:
        return f"{symbol}{value / THOUSAND:.0f} K"
    return fmt_money(minor, currency, decimals=False)


SIGNIFICANT_FIGURES = 2


def round_estimate(minor: int) -> int:
    """Two significant figures: an estimate, not a bill (6,788,300 -> 6,800,000)."""
    if minor == 0:
        return 0
    digits = len(str(abs(minor)))
    step: int = 10 ** max(0, digits - SIGNIFICANT_FIGURES)
    return int((Decimal(minor) / step).quantize(Decimal(1), rounding=ROUND_HALF_UP)) * step


TRAILING_ZEROS = re.compile(r"\.0+ (L|Cr|M|K)$|(\.\d*?[1-9])0+ (L|Cr|M|K)$")


def _estimate(minor: int, currency: str) -> str:
    """A rounded headline figure without trailing zeros ('Rs 33 L', 'Rs 2.9 Cr')."""
    text = fmt_headline(round_estimate(minor), currency)
    return TRAILING_ZEROS.sub(
        lambda m: f" {m.group(1)}" if m.group(1) else f"{m.group(2)} {m.group(3)}", text
    )


def fmt_range(low: int | None, high: int | None, currency: str) -> str:
    """'Rs 58,000 - Rs 92,000', rounded; 'about Rs 68,000' when both ends round alike."""
    if low is None or high is None:
        return "-"
    a, b = _estimate(low, currency), _estimate(high, currency)
    return f"about {a}" if a == b else f"{a} - {b}"


def fmt_approx(minor: int | None, currency: str) -> str:
    return "-" if minor is None else f"about {_estimate(minor, currency)}"


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
    currency: str = "INR"
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
        summary=summarise(estimate, project, cfg, margin_visible=margin_visible),
        result=result,
        lines=lines,
        margin_visible=margin_visible,
        currency=estimate.inputs_snapshot["rate_card"].get("currency", "INR"),
        document_name=doc.filename if doc else None,
        prebid=prebid,
    )
