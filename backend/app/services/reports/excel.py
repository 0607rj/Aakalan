"""Excel BoQ (openpyxl). Amounts are exact rupees (paise / 100) formatted to two decimals."""

import io
from collections.abc import Iterable, Sequence
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.services.reports.data import ReportData, rupees

MONEY = "#,##,##0.00"
HEADER = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F2A44")
TITLE = Font(bold=True, size=14)
WIDE = 60
NORMAL = 16


def _money(paise: int | None) -> Any:
    return None if paise is None else float(rupees(paise))


def _table(
    ws: Worksheet, headers: Sequence[str], rows: Iterable[Sequence[Any]], money_cols: set[int]
) -> None:
    ws.append(list(headers))
    for cell in ws[ws.max_row]:
        cell.font, cell.fill = HEADER, HEADER_FILL
    for row in rows:
        ws.append(list(row))
        for col in money_cols:
            ws.cell(row=ws.max_row, column=col).number_format = MONEY
    for i, h in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(i)].width = (
            WIDE if h in {"Item", "Query", "Assumption", "Clauses"} else NORMAL
        )
    ws.freeze_panes = "A2"


def build_boq(data: ReportData) -> bytes:
    e, s, r = data.estimate, data.summary, data.result
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Summary"
    ws.append([f"Cost estimate: {data.project_name}"])
    ws["A1"].font = TITLE
    facts: list[tuple[str, Any]] = [
        ("Estimate version", e.version),
        ("Prepared on", e.created_at.date().isoformat()),
        ("Rate card / parameters", f"{e.rate_card_version} / {e.parameter_set_version}"),
        ("Seed", e.seed),
        ("Low (P10)", _money(e.p10_paise)),
        ("Most likely (P50)", _money(e.p50_paise)),
        ("High (P90)", _money(e.p90_paise)),
        ("Base case (sum of most-likely values)", _money(e.likely_paise)),
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
            ws.cell(row=ws.max_row, column=2).number_format = MONEY
    ws.append([])
    ws.append(["Where the money goes", "Amount", "Share %"])
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)
    for part in s.parts:
        ws.append([part.label, _money(part.amount_paise), part.share_percent])
        ws.cell(row=ws.max_row, column=2).number_format = MONEY
    ws.column_dimensions["A"].width = WIDE
    ws.column_dimensions["B"].width = 22

    lines = wb.create_sheet("Cost lines")
    _table(
        lines,
        ["#", "Stage", "Bucket", "Year", "Item", "Low", "Likely", "High", "Formula", "Clauses"],
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
            sheet,
            ["Item", "Low", "Likely", "High"],
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

    manpower = wb.create_sheet("Manpower")
    _table(
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
        prebid = wb.create_sheet("Pre-bid queries")
        _table(
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
