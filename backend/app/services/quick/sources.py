"""Where every price comes from (OPEN_QUESTIONS 226), read from the engine's own trace of each
cost line and the catalog pinned in the estimate's snapshot, so it holds for any project with
nothing written per project: a numbered list of sources (day rates and prices with their
published source and link, the hours behind each building block with their evidence, the
settings the formulas used, the studies behind the AI saving) and, for every row of the results
page (an item of "What's inside the price", a feature's building cost), the sources it rests on,
the work, the rates and the document sentences that asked for it.

Each source says honestly what it is: `published` (a named public source, with a link when there
is one), `worked_out` (computed from other published prices, e.g. an all-in hosting price from
the cloud price list) or `estimate` (our reasoned figure, not yet checked against a published
one). Shown only, never priced. Margin lines and their settings are left out for users who may
not see margin; a block shared from another company's research shows its public web pages but
never the words it was researched under (OPEN_QUESTIONS 185)."""

from collections.abc import Iterable
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel

from app.models import CostLine, Estimate
from app.services.quick.config import QuickConfig
from app.services.quick.service import STANDARD_BLOCKS, cost_item_of, feature_owners
from app.services.research.library import SHARED_PREFIX

Status = Literal["published", "worked_out", "estimate", "your_choice"]
MARGIN_BUCKET = "commercial.margin"
AI_GROUP = "ai_productivity"
MARGIN = "margin_percent"
TASK_SAVINGS = "ai_productivity.task_savings."
PLACEHOLDER = "placeholder"
WORKED_OUT = ("derived from", "worked out from")
REASONED_ONLY = "expert_judgement"
UNITS = {
    "per_person_day": "a day",
    "per_month": "a month",
    "per_year": "a year",
    "per_million_tokens": "per million AI tokens",
    "per_seat_month": "a person a month",
    "per_instance_month": "a server a month",
    "inr_per_usd": "rupees per dollar",
    "ratio_per_year": "of the amount a year",
    "per_server": "each",
    "per_device": "each",
    "per_rack": "each",
    "per_ups": "each",
    "per_site": "each site",
    "per_server_year": "a server a year",
    "per_device_year": "a device a year",
    "per_tb_capex": "a TB",
    "per_server_capex": "a server",
    "per_rack_month": "a rack a month",
}
WORDS = {"qa": "QA", "ui": "UI", "ux": "UX", "ml": "ML", "devops": "DevOps", "ai": "AI"}


class Cite(BaseModel):
    """One piece of evidence inside a source (a page of published hours, a study)."""

    text: str
    url: str | None = None
    year: int | None = None
    checked: bool | None = None  # studies: finding read on the page (None = not a study)


class Source(BaseModel):
    n: int  # its number in the list, cited by the rows as [n]
    kind: Literal["rate", "hours", "setting", "ai_saving", "answers", "margin"]
    title: str
    detail: str  # the source as written in the reference data
    url: str | None = None
    version: str  # rate card / catalog / parameter set version pinned in the estimate
    status: Status
    confidence: str | None = None  # hours: the catalog's own confidence word
    values: list[str] = []  # settings: the values this estimate used ("medium = 1.0")
    cites: list[Cite] = []
    amount: str | None = None  # rates: the price (Decimal string, major units)
    currency: str | None = None  # rates: its currency
    role: bool = False  # rates: a person's day rate (role.*)


class Rate(BaseModel):
    label: str
    amount: str  # Decimal string, major units
    currency: str
    unit: str


class Asked(BaseModel):
    """A document sentence (or typed feature) that asked for the work."""

    text: str
    page: int | None
    clause: str | None


class AiTask(BaseModel):
    task: str
    saving_percent: int
    confidence: Literal["medium", "low"] | None


class RowSources(BaseModel):
    row: str  # "item:<group>:<key>" or "feature:<label>" (the results page's rows)
    sources: list[int]
    person_days: str | None = None  # the work behind it (most likely), Decimal string
    rates: list[Rate] = []
    asked: list[Asked] = []
    ai_tasks: list[AiTask] = []  # the AI saving applied to its work, by task


class EstimateSources(BaseModel):
    sources: list[Source]
    rows: list[RowSources]
    counts: dict[Status, int]


def _rate_status(item: dict[str, Any]) -> Status:
    text = str(item.get("source") or "").strip().lower()
    if not text or text.startswith(PLACEHOLDER):
        return "estimate"
    if text.startswith(WORKED_OUT):
        return "worked_out"
    return "published"


def _setting_status(source: str) -> Status:
    return "estimate" if source.strip().lower().startswith(PLACEHOLDER) else "published"


def _humane(key: str) -> str:
    words = key.rsplit(".", 1)[-1].lower().split("_")
    text = " ".join(WORDS.get(w, w) for w in words)
    return text[:1].upper() + text[1:]


def rate_title(cfg: QuickConfig, key: str, unit: str) -> str:
    """A price's plain name: the longest matching `rate_labels` prefix ({name} = its key's last
    part, e.g. "QA engineer day rate"), else its key in words, with its unit."""
    labels = cfg.price_sources.rate_labels if cfg.price_sources else {}
    prefix = max((p for p in labels if key.startswith(p)), key=len, default=None)
    name = labels[prefix].format(name=_humane(key)) if prefix else _humane(key)
    if prefix == "role.":
        return name
    return f"{name} ({UNITS.get(unit, unit.replace('_', ' '))})"


def _value(v: object) -> str:
    if isinstance(v, dict):
        return ", ".join(f"{k} {_value(x)}" for k, x in v.items())
    if isinstance(v, list):
        return ", ".join(_value(x) for x in v)
    return str(v)


class _Collector:
    def __init__(self, cfg: QuickConfig, snapshot: dict[str, Any]) -> None:
        self.cfg = cfg
        self.words = cfg.price_sources
        self.catalog = {c["key"]: c for c in snapshot.get("catalog", {}).get("components", [])}
        self.catalog_version = str(snapshot.get("catalog", {}).get("version", ""))
        params = snapshot.get("parameters", {})
        self.params_version = str(params.get("version", ""))
        self.defaults_source = str((params.get("defaults") or {}).get("source", ""))
        self.by_key: dict[str, Source] = {}

    def _add(self, key: str, make: Any) -> Source:
        if key not in self.by_key:
            self.by_key[key] = make(len(self.by_key) + 1)
        return self.by_key[key]

    def rate(self, item: dict[str, Any]) -> Source:
        return self._add(
            f"rate:{item['key']}",
            lambda n: Source(
                n=n,
                kind="rate",
                title=rate_title(self.cfg, item["key"], item["unit"]),
                detail=str(item.get("source") or ""),
                url=item.get("source_url"),
                version=f"rate card {item.get('rate_card_version', '')}",
                status=_rate_status(item),
                amount=str(item["amount"]) if item.get("amount") is not None else None,
                currency=str(item.get("currency") or "") or None,
                role=str(item["key"]).startswith("role."),
            ),
        )

    def hours(self, catalog_key: str) -> Source | None:
        comp = self.catalog.get(catalog_key)
        if comp is None:
            return None
        shared = catalog_key.startswith(SHARED_PREFIX)
        evidence = comp.get("evidence") or []
        reasoned = not evidence or all(e.get("source_type") == REASONED_ONLY for e in evidence)
        cites = [
            Cite(text=str(e.get("citation", "")), url=e.get("url"), year=e.get("published"))
            for e in evidence
            # a shared block's AI analysis names another company's feature: left out
            if not (shared and e.get("source_type") == REASONED_ONLY)
        ]
        return self._add(
            f"hours:{catalog_key}",
            lambda n: Source(
                n=n,
                kind="hours",
                title="Hours for a researched feature"
                if shared
                else f"Hours for {comp.get('name', catalog_key)}",
                detail="Hours from published pages, checked by the app"
                if shared
                else str(comp.get("source", "")),
                version=f"catalog {self.catalog_version}",
                status="estimate" if reasoned else "published",
                confidence=str(comp.get("confidence") or "") or None,
                cites=cites,
            ),
        )

    def setting(self, param: dict[str, Any]) -> Source:
        path = str(param["path"])
        group = path.split(".", 1)[0]
        if group == AI_GROUP:
            return self.ai_saving(param)
        label = (self.words.settings.get(group) if self.words else None) or _humane(group)
        src = self._add(
            f"setting:{group}",
            lambda n: Source(
                n=n,
                kind="setting",
                title=label,
                detail=str(param.get("source", "")),
                version=f"parameter set {param.get('parameter_set_version', '')}",
                status=_setting_status(str(param.get("source", ""))),
            ),
        )
        shown = f"{path.split('.', 1)[-1].replace('_', ' ')} = {_value(param['value'])}"
        if shown not in src.values:
            src.values.append(shown)
        return src

    def answers(self, driver: dict[str, Any]) -> Source:
        """The project's answers and company settings a line used (one source for all): what
        the user chose, or the usual answer the engine took for a question left open."""
        src = self._add(
            "answers",
            lambda n: Source(
                n=n,
                kind="answers",
                title="Project details you gave",
                detail="What the project is, as given on the form or read from the document "
                "(users, hosting, years of support ...); 'usual answer' where a question was "
                "left open",
                version="this estimate",
                status="your_choice",
            ),
        )
        how = "you chose" if driver.get("source") == "user" else "usual answer"
        shown = f"{str(driver['key']).replace('_', ' ')} = {_value(driver['value'])} ({how})"
        if shown not in src.values:
            src.values.append(shown)
        return src

    def margin(self, driver: dict[str, Any]) -> Source:
        """The builder's profit: one figure for everyone, from the parameter set, with its
        source (OPEN_QUESTIONS 227)."""
        percent = f"{Decimal(str(driver['value'])) * 100:.0f}%"
        checked = self.words.margin if self.words else None
        return self._add(
            "margin",
            lambda n: Source(
                n=n,
                kind="margin",
                title="Builder's profit",
                detail=checked.summary if checked else self.defaults_source,
                version=f"parameter set {self.params_version}",
                # one figure checked against published margins, not itself a published number
                status="worked_out" if checked else _setting_status(self.defaults_source),
                values=[f"profit = {percent} added on the cost"],
                cites=[
                    Cite(text=f"{f.name}: {f.finding}", url=f.url, year=f.year, checked=f.checked)
                    for f in (checked.figures if checked else [])
                ],
            ),
        )

    def ai_saving(self, param: dict[str, Any]) -> Source:
        studies = self.words.ai_studies if self.words else []
        src = self._add(
            "ai_saving",
            lambda n: Source(
                n=n,
                kind="ai_saving",
                title=(self.words.settings.get(AI_GROUP) if self.words else None)
                or "Time AI tools save",
                detail=str(param.get("source", "")),
                version=f"parameter set {param.get('parameter_set_version', '')}",
                status="published",
                cites=[
                    Cite(text=f"{s.name}: {s.finding}", url=s.url, year=s.year, checked=s.checked)
                    for s in studies
                ],
            ),
        )
        path = str(param["path"])
        if path.startswith(TASK_SAVINGS):
            task = path[len(TASK_SAVINGS) :]
            label = (self.words.tasks.get(task) if self.words else None) or _humane(task)
            shown = f"{label}: {Decimal(str(param['value'])) * 100:.0f}% saved"
            if shown not in src.values:
                src.values.append(shown)
        return src


def _ai_tasks(cfg: QuickConfig, params: Iterable[dict[str, Any]]) -> list[AiTask]:
    words = cfg.price_sources
    out = []
    for p in params:
        path = str(p["path"])
        if not path.startswith(TASK_SAVINGS):
            continue
        task = path[len(TASK_SAVINGS) :]
        out.append(
            AiTask(
                task=(words.tasks.get(task) if words else None) or _humane(task),
                saving_percent=int((Decimal(str(p["value"])) * 100).to_integral_value()),
                confidence=words.ai_task_confidence.get(task) if words else None,
            )
        )
    return out


def _row_add(rows: dict[str, dict[str, Any]], row: str, ln: CostLine, found: list[int]) -> None:
    trace = ln.trace or {}
    acc = rows.setdefault(
        row,
        {"sources": [], "pd": Decimal(0), "rates": {}, "asked": {}, "ai": {}, "people": False},
    )
    for n in found:
        if n not in acc["sources"]:
            acc["sources"].append(n)
    pd = sum((Decimal(str(v)) for v in (ln.role_pd or {}).values()), Decimal(0))
    if pd:
        acc["pd"] += pd
        acc["people"] = True
    for r in trace.get("rate_items", []):
        acc["rates"].setdefault(r["key"], r)
    for q in trace.get("requirements", []):
        acc["asked"].setdefault(q["text"], q)


def estimate_sources(
    cfg: QuickConfig, estimate: Estimate, *, margin_visible: bool
) -> EstimateSources:
    """Every source the estimate used, numbered in the order the rows first need them, and the
    sources, work, rates, asking sentences and AI saving behind each results-page row."""
    collect = _Collector(cfg, estimate.inputs_snapshot)
    owners = feature_owners(estimate.inputs_snapshot)
    rows: dict[str, dict[str, Any]] = {}
    ai_by_row: dict[str, dict[str, AiTask]] = {}
    for ln in sorted(estimate.lines, key=lambda x: x.sort_order):
        if ln.bucket == MARGIN_BUCKET and not margin_visible:
            continue
        trace = ln.trace or {}
        found: list[int] = []
        component = trace.get("component") or {}
        if component.get("catalog_key"):
            hours = collect.hours(component["catalog_key"])
            if hours is not None:
                found.append(hours.n)
        found += [collect.rate(r).n for r in trace.get("rate_items", [])]
        params = trace.get("parameters", [])
        found += [collect.setting(p).n for p in params]
        for d in trace.get("drivers", []):
            if d.get("value") is None:
                continue
            found.append((collect.margin(d) if d["key"] == MARGIN else collect.answers(d)).n)
        group, key, _, _ = cost_item_of(cfg, ln, margin_visible)
        targets = [f"item:{group}:{key}"]
        cid = ln.line_key.split("/", 1)[1] if "/" in ln.line_key else ""
        if cid in owners:
            # a standard block's row on the results page, as feature_costs groups it
            targets += [f"feature:{label}" for label in owners[cid] or [STANDARD_BLOCKS]]
        tasks = _ai_tasks(cfg, params)
        for row in targets:
            _row_add(rows, row, ln, found)
            for t in tasks:
                ai_by_row.setdefault(row, {}).setdefault(t.task, t)
    sources = sorted(collect.by_key.values(), key=lambda s: s.n)
    counts: dict[Status, int] = {"published": 0, "worked_out": 0, "estimate": 0, "your_choice": 0}
    for s in sources:
        counts[s.status] += 1
    return EstimateSources(
        sources=sources,
        rows=[
            RowSources(
                row=row,
                sources=sorted(acc["sources"]),
                person_days=f"{acc['pd']:.1f}" if acc["people"] else None,
                rates=[
                    Rate(
                        label=rate_title(cfg, r["key"], r["unit"]),
                        amount=str(r["amount"]),
                        currency=str(r.get("currency", "")),
                        unit=UNITS.get(r["unit"], r["unit"]),
                    )
                    for r in acc["rates"].values()
                ],
                asked=[
                    Asked(text=q["text"], page=q.get("page"), clause=q.get("clause_ref"))
                    for q in acc["asked"].values()
                ],
                ai_tasks=list(ai_by_row.get(row, {}).values()),
            )
            for row, acc in rows.items()
        ],
        counts=counts,
    )
