# ruff: noqa: E501  (report layout reads better with long lines)
"""PDF report (reportlab, BSD licence — no system libraries needed on Windows or Docker).

Sections: summary, where the money goes, range drivers and checks, breakdown by stage and
year, cost lines, manpower, assumptions, pre-bid queries, and a trace appendix showing the
formula, tender clauses and rate-card entries behind every line.
"""

import io
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.reports.data import ReportData, fmt_approx, fmt_headline, fmt_money, fmt_range

NAVY = colors.HexColor("#1F2A44")
LIGHT = colors.HexColor("#F1F3F7")
AMBER = colors.HexColor("#8A5A00")
MARGIN = 15 * mm
MAX_STEPS_IN_APPENDIX = 8
STEP_QUANTUM = Decimal("0.0001")

_styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_styles["Heading1"], textColor=NAVY, fontSize=18, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=_styles["Heading2"], textColor=NAVY, fontSize=13, spaceBefore=10)
BODY = ParagraphStyle("Body", parent=_styles["BodyText"], fontSize=9, leading=12)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=7.5, leading=9.5)
NOTE = ParagraphStyle("Note", parent=BODY, textColor=AMBER)
RIGHT = ParagraphStyle("Right", parent=SMALL, alignment=TA_RIGHT)
BIG = ParagraphStyle("Big", parent=BODY, fontSize=20, leading=24, textColor=NAVY)


def _num(value: object) -> str:
    """Display a step value with at most 4 decimals (stored values keep full precision)."""
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        return str(value)
    return (
        f"{d:,.0f}" if d == d.to_integral_value() else f"{d.quantize(STEP_QUANTUM).normalize():f}"
    )


def _p(text: object, style: ParagraphStyle = SMALL) -> Paragraph:
    plain = str(text).replace("₹", "Rs ")  # base PDF fonts have no rupee glyph
    safe = plain.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe, style)


def _table(
    header: Sequence[str], rows: Sequence[Sequence[Any]], widths: Sequence[float], money: set[int]
) -> Table:
    data = [[_p(h) for h in header]]
    for row in rows:
        data.append([_p(v, RIGHT if i in money else SMALL) for i, v in enumerate(row)])
    t = Table(data, colWidths=list(widths), repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, NAVY),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return t


def _footer(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(
        MARGIN,
        8 * mm,
        "Aakalan cost estimate — every figure is computed by a deterministic engine and traced to its source.",
    )
    canvas.drawRightString(A4[0] - MARGIN, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(data: ReportData) -> bytes:
    e, s, r = data.estimate, data.summary, data.result
    width = A4[0] - 2 * MARGIN

    def money(minor: int | None) -> str:
        return fmt_money(minor, data.currency)

    def headline(minor: int | None) -> str:
        return fmt_headline(minor, data.currency)

    def span(low: int | None, high: int | None) -> str:
        return fmt_range(low, high, data.currency)

    def about(minor: int | None) -> str:
        return fmt_approx(minor, data.currency)

    story: list[Any] = [
        Paragraph(f"Cost estimate: {_p(data.project_name, BODY).text}", H1),
        _p(
            f"Version {e.version} · prepared {e.created_at.date().isoformat()} · rate card "
            f"{e.rate_card_version} · parameters {e.parameter_set_version} · seed {e.seed}"
            + (f" · from {data.document_name}" if data.document_name else ""),
            BODY,
        ),
        Spacer(1, 4 * mm),
    ]
    if s.indicative:
        story.append(
            _p(
                "Indicative: some rates and effort factors are placeholders or public "
                "benchmarks, not this company's own costs.",
                NOTE,
            )
        )
    if not s.feasible:
        story += [_p("Not feasible", H2), _p(s.message or "", BODY)]
    else:
        story += [
            Spacer(1, 2 * mm),
            _p(f"Estimated total: {span(s.low_paise, s.high_paise)}", BIG),
            _p(
                f"Most likely {about(s.likely_paise)}. This is an estimate before the work "
                "starts, not a final bill. "
                f"Time to build: about {s.build_months} months. Support included: "
                + (
                    f"{s.support_years} years. "
                    if s.support_years
                    else "none (handed over after launch). "
                )
                + "Cost to build the software only: "
                + f"{span(s.build_only_low_paise, s.build_only_high_paise)}. "
                f"Confidence: {e.confidence}.",
                BODY,
            ),
        ]
        if s.biggest_uncertainty:
            story.append(_p(s.biggest_uncertainty, BODY))
        story += [
            _p("Where the money goes", H2),
            _table(
                ["Part", "Amount", "Share"],
                [
                    [pt.label, span(pt.low_paise, pt.high_paise), f"{pt.share_percent}%"]
                    for pt in s.parts
                ]
                + [["Planned cost (most likely)", about(s.planned_paise), ""]],
                [width * 0.6, width * 0.25, width * 0.15],
                {1, 2},
            ),
        ]
    if s.bid_check:
        c = s.bid_check
        story += [
            _p("Bid check (for planning the tender budget)", H2),
            _p(
                f"Fair range {span(c.fair_low_paise, c.fair_high_paise)}. Bids below "
                f"{about(c.too_low_below_paise)} are probably too low; above "
                f"{about(c.too_high_above_paise)} probably too high. {c.note}",
                BODY,
            ),
        ]
    if s.similar_projects:
        story += [
            _p("Similar real projects (published prices, today's money)", H2),
            _table(
                ["Project", "Client", "Year", "Price"],
                [[p.title, p.client_type.replace("_", " "), p.year,
                  span(p.low_paise, p.high_paise) if p.low_paise else f"up to {about(p.high_paise)}"]
                 for p in s.similar_projects],
                [width * 0.5, width * 0.18, width * 0.08, width * 0.24],
                {3},
            ),
        ]  # fmt: skip
    if s.cost_items:
        rows: list[list[Any]] = []
        group = None
        for item in s.cost_items:
            if item.group_label != group:
                group = item.group_label
                rows.append([group.upper(), "", ""])
            work = (
                f"{item.person_days_low:,}-{item.person_days_high:,} person-days"
                if item.person_days
                and item.person_days_low is not None
                and item.person_days_high is not None
                else ""
            )
            rows.append([f"- {item.label}", work, span(item.low_paise, item.high_paise)])
        story += [
            _p("What's inside the price", H2),
            _table(
                ["Item", "Work", "Amount"], rows, [width * 0.6, width * 0.18, width * 0.22], {2}
            ),
        ]
    if s.client_pays:
        story += [
            _p("Paid directly by the client (not in this price)", H2),
            _table(
                ["Item", "First year", f"Over {s.support_years} years" if s.support_years else "Per year"],
                [
                    [c.label + (f" — {c.note}" if c.note else ""),
                     span(c.first_year_low_paise, c.first_year_high_paise)
                     if c.first_year_paise is not None else "-",
                     span(c.total_low_paise, c.total_high_paise)
                     if c.total_paise is not None else "-"]
                    for c in s.client_pays
                ],
                [width * 0.56, width * 0.22, width * 0.22],
                {1, 2},
            ),
        ]  # fmt: skip
    if r.get("top_drivers_text") or r.get("sanity_checks"):
        story.append(_p("Range drivers and checks", H2))
        if r.get("top_drivers_text"):
            story.append(_p(r["top_drivers_text"], BODY))
        for check in r.get("sanity_checks", []):
            story.append(
                _p(("Check: " if check["status"] == "ok" else "Flag: ") + check["message"], BODY)
            )
    tl = r["timeline"]
    story.append(
        _p(
            f"Timeline: natural duration {tl['natural_duration_months']} months; delivery "
            f"{tl['delivery_duration_months']} months ({tl['status']}); size band {tl['size_band']}.",
            BODY,
        )
    )
    for title, key in (("By stage", "by_stage"), ("By year", "by_year")):
        if r[key]:
            story += [
                _p(title, H2),
                _table(
                    ["Item", "Low", "Likely", "High"],
                    [
                        [
                            g["name"],
                            money(g["low_paise"]),
                            money(g["likely_paise"]),
                            money(g["high_paise"]),
                        ]
                        for g in r[key]
                    ],
                    [width * 0.4, width * 0.2, width * 0.2, width * 0.2],
                    {1, 2, 3},
                ),
            ]
    if data.lines:
        story += [
            PageBreak(),
            _p("Cost lines", H2),
            _table(
                ["#", "Item", "Year", "Low", "Likely", "High"],
                [
                    [ln.number, f"{ln.bucket_name}: {ln.label}" + (" (restricted)" if ln.redacted else ""),
                     ln.year, money(ln.low_paise), money(ln.likely_paise), money(ln.high_paise)]
                    for ln in data.lines
                ],
                [width * 0.06, width * 0.43, width * 0.06, width * 0.15, width * 0.15, width * 0.15],
                {3, 4, 5},
            ),
        ]  # fmt: skip
    if r["manpower"]:
        story += [
            _p("Manpower", H2),
            _table(
                ["Role", "Stage", "Year", "Person-days", "Person-months", "Avg FTE"],
                [
                    [m["role"].removeprefix("role.").replace("_", " "), m["stage"], m["year"],
                     m["person_days"], m["person_months"], m["average_fte"]]
                    for m in r["manpower"]
                ],
                [width * 0.3, width * 0.14, width * 0.08, width * 0.16, width * 0.16, width * 0.16],
                {3, 4, 5},
            ),
        ]  # fmt: skip
    assumptions = [a for a in e.assumptions if data.margin_visible or a.key != "margin_percent"]
    if assumptions:
        story += [_p("Assumptions (defaults used where no answer was given)", H2)]
        story += [_p(f"• {a.text}", SMALL) for a in assumptions]
    if data.prebid:
        story += [_p("Questions to ask the client", H2)]
        for q in data.prebid:
            where = f" (clause {q.clause_ref or '-'}, page {q.page})" if q.page else ""
            story.append(_p(f"{q.number}. {q.query}{where}", BODY))
    if data.lines:
        story += [PageBreak(), _p("Trace appendix", H2)]
        for ln in data.lines:
            if ln.redacted:
                continue
            block: list[Any] = [
                _p(
                    f"{ln.number}. {ln.bucket_name}: {ln.label} (year {ln.year}) — likely {money(ln.likely_paise)}",
                    BODY,
                ),
                _p(f"Formula {ln.formula_id}: {ln.formula}", SMALL),
            ]
            for req in ln.requirements:
                block.append(
                    _p(
                        f"Requirement {req['code']} — clause {req['clause_ref'] or '-'}, page {req['page'] or '-'}: {req['text']}",
                        SMALL,
                    )
                )
            for it in ln.rate_items:
                block.append(
                    _p(
                        f"Rate {it['key']} = {it['amount']} {it['currency']} {it['unit']} (rate card {it['rate_card_version']}; source: {it['source']})",
                        SMALL,
                    )
                )
            for st in ln.steps[:MAX_STEPS_IN_APPENDIX]:
                block.append(
                    _p(f"Step: {st['label']} — {st['expression']} = {_num(st['value'])}", SMALL)
                )
            block.append(Spacer(1, 2 * mm))
            story.append(KeepTogether(block))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
        title=f"Cost estimate: {data.project_name}", author="Aakalan",
    )  # fmt: skip
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
