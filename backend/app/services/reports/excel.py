"""Excel BoQ (openpyxl). Amounts are exact rupees (paise / 100) formatted to two decimals."""

import io
from collections.abc import Iterable, Sequence
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.services.reports.data import QUOTE_COVERS, SOURCE_STATUS, ReportData, rupees

MONEY_INR = "#,##,##0.00"  # Indian digit grouping
MONEY_OTHER = "#,##0.00"
HEADER = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F2A44")
TITLE = Font(bold=True, size=14)
WIDE = 60
NORMAL = 16
WIDE_COLUMNS = {"Item", "Query", "Assumption", "Clauses", "Question", "Why", "Other answers"}


def _money(paise: int | None) -> Any:
    return None if paise is None else float(rupees(paise))


def _table(
    money_fmt: str,
    ws: Worksheet,
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
    money_cols: set[int],
) -> None:
    ws.append(list(headers))
    for cell in ws[ws.max_row]:
        cell.font, cell.fill = HEADER, HEADER_FILL
    for row in rows:
        ws.append(list(row))
        for col in money_cols:
            ws.cell(row=ws.max_row, column=col).number_format = money_fmt
    for i, h in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(i)].width = WIDE if h in WIDE_COLUMNS else NORMAL
    ws.freeze_panes = "A2"


def build_boq(data: ReportData) -> bytes:
    e, s, r = data.estimate, data.summary, data.result
    money_fmt = MONEY_INR if data.currency == "INR" else MONEY_OTHER
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Summary"
    ws.append([f"Cost estimate: {data.project_name} (amounts in {data.currency})"])
    ws["A1"].font = TITLE
    facts: list[tuple[str, Any]] = [
        ("Estimate version", e.version),
        ("Prepared on", e.created_at.date().isoformat()),
        ("Rate card / parameters", f"{e.rate_card_version} / {e.parameter_set_version}"),
        ("Seed", e.seed),
        ("Low (P10)", _money(e.p10_paise)),
        ("Likely price (P50: planned cost + expected overrun, with GST)", _money(e.p50_paise)),
        ("High (P90)", _money(e.p90_paise)),
        (
            "Planned cost (sum of the planned lines, before the expected overrun)",
            _money(e.likely_paise),
        ),
        ("Likely price without GST", _money(s.likely_without_tax_paise)),
        ("Cost to build only", _money(s.build_only_paise)),
        ("Time to build (months)", s.build_months),
        ("Support after launch (years)", s.support_years),
        ("Confidence", e.confidence),
        ("Calibration", "Indicative (uses placeholder values)" if s.indicative else "Calibrated"),
        ("Biggest uncertainty", s.biggest_uncertainty or ""),
    ]
    for label, value in facts:
        ws.append([label, value])
        if isinstance(value, float):
            ws.cell(row=ws.max_row, column=2).number_format = money_fmt
    ws.append([])
    ws.append(["Where the money goes", "Low", "Planned", "High", "Share %"])
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)
    for part in s.parts:
        ws.append([
            part.label, _money(part.low_paise), _money(part.amount_paise),
            _money(part.high_paise), part.share_percent,
        ])  # fmt: skip
        for col in (2, 3, 4):
            ws.cell(row=ws.max_row, column=col).number_format = money_fmt
    ws.column_dimensions["A"].width = WIDE
    ws.column_dimensions["B"].width = 22

    lines = wb.create_sheet("Cost lines")
    _table(
        money_fmt,
        lines,
        ["#", "Stage", "Bucket", "Year", "Item", "Low", "Planned", "High", "Formula", "Clauses"],
        (
            [
                ln.number,
                ln.stage,
                ln.bucket_name,
                ln.year,
                ln.label + (" (restricted)" if ln.redacted else ""),
                _money(ln.low_paise),
                _money(ln.likely_paise),
                _money(ln.high_paise),
                ln.formula_id,
                "; ".join(
                    f"{q['code']} cl. {q['clause_ref'] or '-'} p. {q['page'] or '-'}"
                    for q in ln.requirements
                ),
            ]
            for ln in data.lines
        ),
        {6, 7, 8},
    )

    for title, key in (("By stage", "by_stage"), ("By year", "by_year")):
        sheet = wb.create_sheet(title)
        groups = r[key]
        _table(
            money_fmt,
            sheet,
            ["Item", "Low", "Planned", "High"],
            (
                [
                    g["name"],
                    _money(g["low_paise"]),
                    _money(g["likely_paise"]),
                    _money(g["high_paise"]),
                ]
                for g in groups
            ),
            {2, 3, 4},
        )

    if s.cost_items:
        inside = wb.create_sheet("Inside the price")
        _table(
            money_fmt,
            inside,
            ["Group", "Item", "Person-days", "Low", "Planned", "High", "Sources"],
            (
                [
                    i.group_label,
                    i.label,
                    i.person_days or "",
                    _money(i.low_paise),
                    _money(i.amount_paise),
                    _money(i.high_paise),
                    data.row_sources(f"item:{i.group}:{i.key}"),
                ]
                for i in s.cost_items
            ),
            {4, 5, 6},
        )

    if s.client_pays:
        client = wb.create_sheet("Paid by client")
        _table(
            money_fmt,
            client,
            [
                "Item",
                "First year",
                f"Over {s.support_years} years" if s.support_years else "Per year",
                "Note",
            ],
            (
                [c.label, _money(c.first_year_paise), _money(c.total_paise), c.note or ""]
                for c in s.client_pays
            ),
            {2, 3},
        )

    if s.assumed:
        assumed = wb.create_sheet("Assumed answers")
        _table(
            money_fmt,
            assumed,
            ["Question", "Assumed answer (change if wrong)", "Meaning"],
            ([a.question, a.answer, a.detail] for a in s.assumed),
            set(),
        )
    not_included = data.not_included_rows()
    if not_included:
        excluded = wb.create_sheet("Not included")
        _table(money_fmt, excluded, ["Item", "Why"], not_included, set())
    open_rows = data.open_rows()
    if open_rows:
        open_sheet = wb.create_sheet("Open answers")
        _table(money_fmt, open_sheet, ["Question", "Priced as", "Other answers"], open_rows, set())

    hardware = data.summary.hardware
    if hardware is not None:  # own servers, or asked for (OPEN_QUESTIONS 231)
        hw_sheet = wb.create_sheet("Hardware")
        who = (
            "The client buys these: not in the price"
            if hardware.who_buys == "client_buys"
            else "In the price: buying it, its AMC and yearly licences"
            if hardware.once_paise is not None
            else "Servers and storage in the price; network, rack and licences not priced yet"
        )
        _table(
            money_fmt,
            hw_sheet,
            ["Site", "Item", "How many", "Size", "Price each", "Total", "Paid", "Why",
             "Who buys", "Sized by", "Price from"],
            (
                [i.site, i.label, i.quantity, i.spec,
                 _money((i.unit_paise or 0) * (i.tb or 1)) if i.unit_paise is not None else None,
                 _money(i.amount_paise) if i.unit_paise is not None else None,
                 "each year" if i.yearly else "once", i.why, who,
                 f"our estimate (parameter set {hardware.parameter_set_version})",
                 ", ".join(i.rate_keys)]
                for i in hardware.items
            ),
            {5, 6},
        )  # fmt: skip

    manpower = wb.create_sheet("Manpower")
    _table(
        money_fmt,
        manpower,
        ["Role", "Stage", "Year", "Person-days", "Person-months", "Average FTE"],
        (
            [m["role"].removeprefix("role."), m["stage"], m["year"], float(m["person_days"]),
             float(m["person_months"]), float(m["average_fte"])]
            for m in r["manpower"]
        ),
        set(),
    )  # fmt: skip

    assumptions = wb.create_sheet("Assumptions")
    _table(
        money_fmt,
        assumptions,
        ["Key", "Assumption"],
        ([a.key, a.text] for a in data.assumptions()),
        set(),
    )

    if data.prebid:
        prebid = wb.create_sheet("Questions for client")
        _table(
            money_fmt,
            prebid,
            ["#", "Clause", "Page", "Query"],
            ([q.number, q.clause_ref, q.page or "", q.query] for q in data.prebid),
            set(),
        )
        for row in prebid.iter_rows(min_row=2):
            row[3].alignment = Alignment(wrap_text=True, vertical="top")

    if data.quotes is not None and data.quotes.quotes:
        quotes = wb.create_sheet("Quotes compared")
        _table(
            money_fmt,
            quotes,
            ["Quote from", "Covers", "Amount (before tax)", "Against likely", "What it tells you"],
            ([n, c, _money(a), vs, w] for n, c, a, vs, w in data.quote_rows()),
            {3},
        )
        quotes.column_dimensions["E"].width = WIDE
        quotes.append([])
        for rng in data.quotes.ranges:
            quotes.append(
                [f"Range, {QUOTE_COVERS[rng.covers].lower()}", "", _money(rng.low_paise), "low"]
            )
            quotes.append(["", "", _money(rng.likely_paise), "likely"])
            quotes.append(["", "", _money(rng.high_paise), "high"])
            for row in quotes.iter_rows(min_row=quotes.max_row - 2, max_row=quotes.max_row):
                row[2].number_format = money_fmt

    if data.sources is not None and data.sources.sources:
        sources = wb.create_sheet("Sources")
        _table(
            money_fmt,
            sources,
            ["#", "Source", "What it is", "Status", "Link", "Version", "Values used", "Evidence"],
            (
                [
                    s.n,
                    s.title,
                    s.detail,
                    SOURCE_STATUS[s.status],
                    s.url or "",
                    s.version,
                    "; ".join(s.values),
                    "; ".join(c.text + (f" ({c.url})" if c.url else "") for c in s.cites),
                ]
                for s in data.sources.sources
            ),
            set(),
        )
        for row in sources.iter_rows(min_row=2):
            for cell in (row[2], row[6], row[7]):
                cell.alignment = Alignment(wrap_text=True, vertical="top")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
