"""Excel BoQ (openpyxl). Amounts are exact rupees (paise / 100) formatted to two decimals."""

import io
from collections.abc import Iterable, Sequence
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.services.reports.data import ReportData, rupees

MONEY_INR = "#,##,##0.00"  # Indian digit grouping
MONEY_OTHER = "#,##0.00"
HEADER = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F2A44")
TITLE = Font(bold=True, size=14)
WIDE = 60
NORMAL = 16


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
        ws.column_dimensions[get_column_letter(i)].width = (
            WIDE if h in {"Item", "Query", "Assumption", "Clauses"} else NORMAL
        )
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
        ("Likely price (P50: planned cost + risk allowance, with GST)", _money(e.p50_paise)),
        ("High (P90)", _money(e.p90_paise)),
        ("Planned cost (sum of the planned lines, before the risk allowance)", _money(e.likely_paise)),
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
            ["Group", "Item", "Person-days", "Low", "Planned", "High"],
            (
                [
                    i.group_label,
                    i.label,
                    i.person_days or "",
                    _money(i.low_paise),
                    _money(i.amount_paise),
                    _money(i.high_paise),
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
        (
            [a.key, a.text]
            for a in e.assumptions
            if data.margin_visible or a.key != "margin_percent"
        ),
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

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
