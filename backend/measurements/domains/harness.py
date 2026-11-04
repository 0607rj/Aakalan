"""Five-domain reading measurement (OPEN_QUESTIONS 205). Not part of the test suite.

Stand-in readers (a model on the user's Claude plan, never the API) answer the exact prompts
the app sends; their JSON replies are run through the app's own code with a FakeClient.

  prep <work>                  write the prompts (system + user per document) and schemas
  gap-user <work> <run> <doc>  after <work>/run<run>/<doc>.first.json: the second-pass prompt
  evaluate <work>              every reading vs the answer files, and run A vs run B

Run from backend/ with ANTHROPIC_API_KEY blank. The answer files are read only by `evaluate`.
"""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

os.environ["ANTHROPIC_API_KEY"] = ""

import yaml

from app.core.config import get_settings
from app.llm.client import FakeClient, load_prompt
from app.services.calibration.backtest import priced_range, reference_for
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.merge import merge_extractions
from app.services.extraction.tender import (
    GAP_PROMPT_FILE,
    ExtractionOutput,
    GapOutput,
    TenderExtraction,
    _covered,
    _fence,
    ai_read,
    build_prompt,
    included_list,
    verify_findings,
)
from app.services.quick.config import quick_config
from app.services.quick.context import missing_prerequisites, project_type
from app.services.quick.prefill import review_prefill
from app.services.quick.service import plan_quick, request_features
from app.services.seeding.reference import load_reference

HERE = Path(__file__).parent
DOCS = [
    "hospital_hms",
    "logistics_fleet",
    "fintech_lending",
    "video_meet",
    "beekeeping_coop",
    "school_erp",
    "insurance_claims",
    "hotel_booking",
    "factory_maintenance",
    "legal_services",
]
RUNS = ["A", "B"]
CFG = quick_config()


def document(name: str) -> ParsedDocument:
    texts = (HERE / "documents" / f"{name}.md").read_text(encoding="utf-8").split("<!-- page -->")
    pages = [Page(i + 1, t) for i, t in enumerate(texts)]
    return ParsedDocument(kind="text", pages=pages, approximate_pages=False)


def gap_system() -> str:
    custom = "\n".join(f"- {k}: {t.label}" for k, t in CFG.custom_feature_types.items())
    features = "\n".join(f"- {f.key}: {f.label}" for f in CFG.features)
    return (
        load_prompt(GAP_PROMPT_FILE)
        .replace("{custom_types}", custom)
        .replace("{features}", features)
        .replace("{included}", included_list(CFG))
    )


def prep(work: Path) -> None:
    p = work / "prompts"
    p.mkdir(parents=True, exist_ok=True)
    (p / "system_first.md").write_text(build_prompt(CFG), encoding="utf-8")
    (p / "system_gap.md").write_text(gap_system(), encoding="utf-8")
    for out, model in (("schema_first.json", ExtractionOutput), ("schema_gap.json", GapOutput)):
        (p / out).write_text(json.dumps(model.model_json_schema(), indent=1), encoding="utf-8")
    for name in DOCS:
        user = _fence(document(name)) + "\n\nRead the tender above and return your findings."
        (p / f"user_{name}.md").write_text(user, encoding="utf-8")
    for r in RUNS:
        (work / f"run{r}").mkdir(exist_ok=True)
    sys.stdout.write(f"written to {p}\n")


def gap_user(work: Path, run: str, name: str) -> None:
    first = ExtractionOutput.model_validate_json(
        (work / f"run{run}" / f"{name}.first.json").read_text(encoding="utf-8")
    )
    user = (
        f"{_fence(document(name))}\n\n<already_found>\n{_covered(first)}\n</already_found>\n\n"
        "Return the requirements the first reading missed."
    )
    out = work / f"run{run}" / f"{name}.gap_user.md"
    out.write_text(user, encoding="utf-8")
    sys.stdout.write(f"valid first reading; second-pass prompt written to {out}\n")


def read(work: Path, run: str, name: str) -> TenderExtraction:
    folder = work / f"run{run}"
    first = json.loads((folder / f"{name}.first.json").read_text(encoding="utf-8"))
    gap_file = folder / f"{name}.gap.json"
    gap = json.loads(gap_file.read_text(encoding="utf-8")) if gap_file.exists() else {}
    gap.setdefault("other_features", [])

    def responder(system: str, user: str) -> object:
        return gap if "<already_found>" in user else first

    d = document(name)
    raw = ai_read(FakeClient(responder), CFG, d).output
    ex = verify_findings(CFG, d, raw, reader="ai", version="stand-in", document=f"{name}.md")
    texts = [{"page": p.number, "text": p.text} for p in d.pages]
    doc = SimpleNamespace(
        kind="rfp", filename=f"{name}.md", page_texts=texts, extraction={"reader": "ai"}
    )
    merged, _ = merge_extractions([(doc, ex)])  # type: ignore[list-item]
    return merged


def _hits(text: str, words: list[str]) -> bool:
    low = text.lower()
    return any(w.lower() in low for w in words)


def _scope_groups(answer: dict[str, Any]) -> list[tuple[list[str], str | None]]:
    """Each expected add-on: the keys any of which counts, and a feature that already brings it."""
    out: list[tuple[list[str], str | None]] = []
    for g in answer.get("scope", []):
        out.append((g, None) if isinstance(g, list) else (g["any"], g.get("or_feature")))
    return out


def score(name: str, ex: TenderExtraction, answer: dict[str, Any]) -> dict[str, Any]:
    req = review_prefill(CFG, ex, "india").request
    ticked = set(request_features(CFG, req))  # ticked, and those an answer adds
    expected, tolerated = set(answer["features"]), set(answer.get("tolerated", []))
    wrong = ticked & set(answer["not_features"])
    unexpected = ticked - expected - tolerated - wrong
    correct = ticked & expected
    offered_scope = {s.key for s in ex.scope}
    names = [o.name for o in ex.other_features]
    hits = {c["what"]: [n for n in names if _hits(n, c["match_any"])] for c in answer["custom"]}
    custom_found = {}
    for c in answer["custom"]:
        found = bool(hits[c["what"]]) or c.get("or_feature") in ticked
        if not found and c.get("or_story_of"):  # a part of another entry, as its stories
            found = bool(hits.get(c["or_story_of"]))
        custom_found[c["what"]] = found
    optional_priced = [
        c["what"]
        for c in answer.get("optional", [])
        if any(_hits(n, c["match_any"]) for n in names)
    ]
    given = {k: str(v) for k, v in req.choices.items() if k in (req.answered or [])}
    warned = [
        w.key
        for w in missing_prerequisites(CFG, sorted(ticked), list(offered_scope), answered=given)
    ]
    want_warned = set(answer.get("prerequisites", [])) | (
        set(answer.get("prerequisites_if_ticked", [])) & ticked
    )
    choices_wrong = {
        q: str(req.choices.get(q))
        for q, v in answer.get("choices", {}).items()
        if str(req.choices.get(q)) != str(v)
    }
    ref = {
        **reference_for(load_reference(get_settings().seeds_dir), "india"),
        "clarity": CFG.requirement_clarity,
    }
    plan = plan_quick(CFG, req, ex.model_dump(mode="json"), f"{name}.md")
    priced = priced_range(plan, req.name, ref, False, None)
    return {
        "domain": ex.project_domain,
        "domain_ok": _hits(ex.project_domain, answer["domain_words"]),
        "project_type": project_type(CFG, sorted(ticked)),
        "user_roles": ex.user_roles,
        "features_ticked": sorted(ticked),
        "feature_levels": dict(sorted(req.feature_levels.items())),
        "expected_n": len(expected),
        "correct_n": len(correct),
        "recall": round(len(correct) / len(expected), 3),
        "precision": round(len(correct) / max(1, len(correct) + len(wrong) + len(unexpected)), 3),
        "missed": sorted(expected - ticked),
        "wrong": sorted(wrong),
        "unexpected": sorted(unexpected),
        "scope_found": sorted(offered_scope),
        "scope_n": len(_scope_groups(answer)),
        "scope_missed": [
            keys
            for keys, feature in _scope_groups(answer)
            if not offered_scope & set(keys) and feature not in ticked
        ],
        "custom_items": [
            f"{o.name} ({o.size}x{o.units}, {len(o.stories)} stories)" for o in ex.other_features
        ],
        "custom_n": len(custom_found),
        "custom_found_n": sum(custom_found.values()),
        "custom_missed": [k for k, v in custom_found.items() if not v],
        "custom_duplicates": {k: v for k, v in hits.items() if len(v) > 1},
        "optional_priced": optional_priced,
        "choices_wrong": choices_wrong,
        "not_priced": sorted(n.topic for n in ex.not_priced),
        "warnings": warned,
        "warnings_ok": set(warned) == want_warned,
        "keywords_added": sorted(f.key for f in ex.features if f.found_by == "keywords"),
        "uncovered": len(ex.uncovered) + ex.uncovered_more,
        "p10_p50_p90_lakh": [round(x / 1e7, 2) for x in priced[:3]] if priced else None,
        "p50_lakh": round(priced[1] / 1e7, 2) if priced else None,
    }


def evaluate(work: Path) -> None:
    out: dict[str, Any] = {}
    for name in DOCS:
        answer = yaml.safe_load((HERE / "answers" / f"{name}.yaml").read_text(encoding="utf-8"))
        row: dict[str, Any] = {}
        for run in RUNS:
            if (work / f"run{run}" / f"{name}.first.json").exists():
                row[run] = score(name, read(work, run, name), answer)
        if len(row) == 2:
            a, b = row["A"], row["B"]
            row["same_features"] = a["features_ticked"] == b["features_ticked"]
            row["same_scope"] = a["scope_found"] == b["scope_found"]
            row["custom_count"] = [len(a["custom_items"]), len(b["custom_items"])]
            pa, pb = a["p50_lakh"], b["p50_lakh"]
            row["p50_gap_pct"] = round(abs(pa - pb) / max(pa, pb) * 100, 1) if pa and pb else None
        out[name] = row
    (HERE / f"results_{work.name}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    sys.stdout.write(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    cmd, work = sys.argv[1], Path(sys.argv[2])
    if cmd == "prep":
        prep(work)
    elif cmd == "gap-user":
        gap_user(work, sys.argv[3], sys.argv[4])
    else:
        evaluate(work)
