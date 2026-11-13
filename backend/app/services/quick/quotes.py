"""Compare quotes (OPEN_QUESTIONS 241): prices someone quoted for the project, typed in by the
user, each placed against the estimate's own low / likely / high range. Nothing here prices
anything: the range is the estimate's, only scaled to what a quote covers, and the quotes are
never fed to the engine.

Quotes are compared before tax, as they are usually written:
- covers "all" (the whole project: build, launch, hosting and support) against the estimate's
  low / likely / high without tax. Tax is a fixed share of every line, so the low and high lose
  the same share as the likely price (likely_without_tax ÷ likely).
- covers "build" (building and launch only) against the "as vendors quote it" building part
  (quote_build_paise, OPEN_QUESTIONS 208); low and high scaled by the same share of the likely.

A quote below the low is "below", above the high "above", else "in". Its difference from the
likely is a whole percent, rounded half up.

Also the feature list to send out for quotes: the same items without our prices
(build_quote_form), so everyone quoting prices the same lines.
"""

import io
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from fastapi import HTTPException, status
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Project, Quote
from app.services.quick.service import QuickSummary

Covers = Literal["all", "build"]
Verdict = Literal["below", "in", "above"]
MAX_QUOTES = 20


class QuoteIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)  # who quoted it
    amount_paise: int = Field(gt=0)  # before tax, minor units of the estimate's currency
    covers: Covers = "all"

    @field_validator("name")
    @classmethod
    def _tidy(cls, v: str) -> str:
        tidy = " ".join(v.split())
        if not tidy:
            raise ValueError("A quote needs a name.")
        return tidy


class QuotesIn(BaseModel):
    quotes: list[QuoteIn] = Field(max_length=MAX_QUOTES)


class QuoteRange(BaseModel):
    """The estimate's range for what a quote covers, before tax."""

    covers: Covers
    low_paise: int
    likely_paise: int
    high_paise: int


class QuoteOut(BaseModel):
    name: str
    amount_paise: int
    covers: Covers
    # None when the estimate has no range for it (not possible by the deadline)
    verdict: Verdict | None
    versus_likely_percent: int | None  # + above the likely, - below it


class QuotesOut(BaseModel):
    currency: str
    ranges: list[QuoteRange]  # "all" first; "build" only when the estimate splits it
    quotes: list[QuoteOut]


def _scaled(amount: int, num: int, den: int) -> int:
    """amount × num ÷ den, rounded half up to whole minor units."""
    return int((Decimal(amount) * num / den).to_integral_value(ROUND_HALF_UP))


def quote_ranges(summary: QuickSummary) -> list[QuoteRange]:
    """The estimate's low / likely / high before tax, for the whole project and, when the
    estimate splits it, for building and launch only. No new number: shares of the range."""
    low, likely, high = summary.low_paise, summary.likely_paise, summary.high_paise
    if not summary.feasible or low is None or likely is None or high is None or likely <= 0:
        return []
    without_tax = summary.likely_without_tax_paise or likely
    ranges = [
        QuoteRange(
            covers="all",
            low_paise=_scaled(low, without_tax, likely),
            likely_paise=without_tax,
            high_paise=_scaled(high, without_tax, likely),
        )
    ]
    build = summary.quote_build_paise
    if build and build < without_tax:
        ranges.append(
            QuoteRange(
                covers="build",
                low_paise=_scaled(low, build, likely),
                likely_paise=build,
                high_paise=_scaled(high, build, likely),
            )
        )
    return ranges


def compare(quote: QuoteIn, ranges: list[QuoteRange]) -> QuoteOut:
    """One quote against the range for what it covers ("build" falls back to the whole
    project's range when the estimate has no separate building part)."""
    by_cover = {r.covers: r for r in ranges}
    rng = by_cover.get(quote.covers) or by_cover.get("all")
    if rng is None:
        return QuoteOut(**quote.model_dump(), verdict=None, versus_likely_percent=None)
    verdict: Verdict = (
        "below"
        if quote.amount_paise < rng.low_paise
        else "above"
        if quote.amount_paise > rng.high_paise
        else "in"
    )
    percent = int(
        (Decimal(quote.amount_paise - rng.likely_paise) * 100 / rng.likely_paise).to_integral_value(
            ROUND_HALF_UP
        )
    )
    return QuoteOut(**quote.model_dump(), verdict=verdict, versus_likely_percent=percent)


def saved_quotes(db: Session, project: Project) -> list[QuoteIn]:
    rows = db.scalars(
        select(Quote)
        .where(Quote.project_id == project.id, Quote.org_id == project.org_id)
        .order_by(Quote.position)
    )
    return [QuoteIn(name=q.name, amount_paise=q.amount_paise, covers=q.covers) for q in rows]  # type: ignore[arg-type]


def save_quotes(db: Session, project: Project, quotes: list[QuoteIn]) -> None:
    """Replace the project's quotes with these, in this order."""
    db.execute(delete(Quote).where(Quote.project_id == project.id, Quote.org_id == project.org_id))
    for i, q in enumerate(quotes):
        db.add(
            Quote(
                org_id=project.org_id,
                project_id=project.id,
                position=i,
                name=q.name,
                amount_paise=q.amount_paise,
                covers=q.covers,
            )
        )
    db.commit()


def quotes_out(db: Session, project: Project, summary: QuickSummary) -> QuotesOut:
    ranges = quote_ranges(summary)
    return QuotesOut(
        currency=summary.currency,
        ranges=ranges,
        quotes=[compare(q, ranges) for q in saved_quotes(db, project)],
    )


# ------------------------------------------------------------------ the feature list to send out

HEADER = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F2A44")
SECTION = Font(bold=True)
MONEY_INR = "#,##,##0.00"
MONEY_OTHER = "#,##0.00"


def quote_form_lines(summary: QuickSummary) -> list[tuple[str, list[tuple[str, str]]]]:
    """(section, [(item, note)]): the features, the launch items and the yearly items the
    estimate has, without any price. Commercial lines (margin, buffer, tax) are left to the
    person quoting; management, testing and design go inside the feature prices."""
    if not summary.feature_costs:
        raise HTTPException(status.HTTP_409_CONFLICT, "This estimate has no feature list.")
    build = [(f.label, f.level or "") for f in summary.feature_costs]
    launch = [
        (c.label, "") for c in summary.cost_items if c.group == "launch" and c.amount_paise > 0
    ]
    run = [
        (c.label, "per year") for c in summary.cost_items if c.group == "run" and c.amount_paise > 0
    ]
    sections = [("Building", build)]
    if launch:
        sections.append(("Launch", launch))
    if run and summary.support_years > 0:
        sections.append((f"Each year after launch ({summary.support_years} years)", run))
    return sections


def build_quote_form(project_name: str, summary: QuickSummary) -> bytes:
    """An Excel sheet of the items to price, with an empty price column and totals that add
    up what the person quoting fills in. Our own prices are not in it."""
    money_fmt = MONEY_INR if summary.currency == "INR" else MONEY_OTHER
    tax = "GST" if summary.currency == "INR" else "tax"
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Items to price"
    ws.append([f"Request for a quote: {project_name}"])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append(
        [
            f"Please price each item below in {summary.currency}, before {tax}. "
            "Include design, testing, project management and your margin in the prices."
        ]
    )
    ws.append(
        [
            f"Building time asked for: {summary.build_months} months. "
            f"Support after launch: {summary.support_years} years."
        ]
    )
    ws.append([])
    ws.append(["#", "Item", "Notes", f"Your price ({summary.currency}, before {tax})"])
    for cell in ws[ws.max_row]:
        cell.font, cell.fill = HEADER, HEADER_FILL
    number = 0
    once_cells: list[str] = []
    yearly_cells: list[str] = []
    for section, items in quote_form_lines(summary):
        ws.append(["", section])
        ws.cell(row=ws.max_row, column=2).font = SECTION
        for item, note in items:
            number += 1
            ws.append([number, item, note, None])
            ws.cell(row=ws.max_row, column=4).number_format = money_fmt
            ref = f"D{ws.max_row}"
            (yearly_cells if section.startswith("Each year") else once_cells).append(ref)
    ws.append([])
    once = f"=SUM({','.join(once_cells)})" if once_cells else 0
    ws.append(["", "Building and launch, total", "", once])
    ws.cell(row=ws.max_row, column=4).number_format = money_fmt
    once_row = ws.max_row
    if yearly_cells:
        ws.append(["", "Each year after launch, total", "", f"=SUM({','.join(yearly_cells)})"])
        ws.cell(row=ws.max_row, column=4).number_format = money_fmt
        year_row = ws.max_row
        ws.append(
            [
                "",
                f"Whole project ({summary.support_years} years of support)",
                "",
                f"=D{once_row}+D{year_row}*{summary.support_years}",
            ]
        )
        ws.cell(row=ws.max_row, column=4).number_format = money_fmt
    for row in ws.iter_rows(min_row=ws.max_row - 2, max_row=ws.max_row):
        row[1].font = SECTION
    for col, width in zip("ABCD", (6, 70, 14, 26), strict=True):
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=6):
        row[1].alignment = Alignment(wrap_text=True, vertical="top")
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
