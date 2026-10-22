"""The AI's second opinion on a finished quick estimate: is the scope the price is built from
right for this project (feature levels, missing or unneeded work)? The AI reads the summary
and names concerns in words; it never gives or changes a number (rule 1): any concern that
contains a digit is dropped. The user decides, edits the features and the engine reprices."""

import re
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.tenancy import scoped
from app.llm.client import get_llm_client, load_prompt
from app.models import Estimate, SecondOpinion, User
from app.services.quick.config import QuickConfig
from app.services.quick.service import QuickSummary

DIGIT = re.compile(r"\d")
Kind = Literal["level_too_high", "level_too_low", "missing", "not_needed", "unclear", "other"]


class Flag(BaseModel):
    kind: Kind
    feature: str | None = Field(default=None, max_length=200)
    message: str = Field(max_length=400)


class Reply(BaseModel):
    verdict: Literal["looks_right", "check"]
    summary: str = Field(default="", max_length=600)
    flags: list[Flag] = []


class SecondOpinionOut(BaseModel):
    verdict: Literal["looks_right", "check"]
    summary: str
    flags: list[Flag]
    created_at: str
    model: str


def estimate_text(summary: QuickSummary) -> str:
    """What the reviewer sees: the scope and how the price splits over it (shares only)."""
    build = sum(f.amount_paise for f in summary.feature_costs) or 1
    lines = [
        f"Project: {summary.name}",
        f"Size: {summary.project_size or 'unknown'}; build time: {summary.build_months} months; "
        f"support after launch: {summary.support_years} years",
        "Features (level, share of the building work):",
        *(
            f"- {f.label} ({f.level or 'set-up every project needs'}, "
            f"{round(100 * f.amount_paise / build)}%)"
            for f in summary.feature_costs
        ),
        "Extra scope: " + (", ".join(summary.scope) or "none"),
        "Team: " + ", ".join(f"{t.label} {t.people}" for t in summary.team),
        "Paid by the client separately: "
        + (", ".join(c.label for c in summary.client_pays) or "none"),
        "Answered 'Not sure': " + (", ".join(summary.not_sure) or "none"),
    ]
    if summary.reality:
        lines.append(
            "Tool's own checks: "
            + "; ".join(f"{c.title} ({'ok' if c.ok else 'check'})" for c in summary.reality.checks)
        )
    return "\n".join(lines)


def clean(reply: Reply, summary: QuickSummary, max_flags: int) -> Reply:
    """Drop concerns with numbers, unknown feature names become general concerns."""
    names = {f.label for f in summary.feature_costs}
    flags = [
        f.model_copy(update={"feature": f.feature if f.feature in names else None})
        for f in reply.flags
        if not DIGIT.search(f.message)
    ][:max_flags]
    text = "" if DIGIT.search(reply.summary) else reply.summary
    verdict = reply.verdict if flags or reply.verdict == "looks_right" else "looks_right"
    return Reply(verdict=verdict, summary=text, flags=flags)


def _out(row: SecondOpinion) -> SecondOpinionOut:
    return SecondOpinionOut(
        verdict="check" if row.verdict == "check" else "looks_right",
        summary=row.summary,
        flags=[Flag.model_validate(f) for f in row.flags],
        created_at=row.created_at.isoformat(),
        model=row.model,
    )


def latest(db: Session, user: User, estimate: Estimate) -> SecondOpinionOut | None:
    row = db.scalars(
        scoped(SecondOpinion, user.org_id).where(SecondOpinion.estimate_id == estimate.id)
    ).first()
    return _out(row) if row else None


def ask(
    db: Session, user: User, cfg: QuickConfig, estimate: Estimate, summary: QuickSummary
) -> SecondOpinionOut:
    """Ask the AI (raises LLMNotConfiguredError without a key) and store the answer."""
    rules = cfg.reality_check
    assert rules is not None
    system = load_prompt(f"{rules.second_opinion_prompt}.md").replace(
        "{{max_flags}}", str(rules.second_opinion_max_flags)
    )
    data = estimate_text(summary).replace("</estimate>", "</ estimate>")  # stays fenced
    result = get_llm_client().extract(
        system=system, user=f"<estimate>\n{data}\n</estimate>", schema=Reply
    )
    reply = clean(result.output, summary, rules.second_opinion_max_flags)
    old = db.scalars(
        scoped(SecondOpinion, user.org_id).where(SecondOpinion.estimate_id == estimate.id)
    ).first()
    if old is not None:
        db.delete(old)
        db.flush()
    row = SecondOpinion(
        org_id=user.org_id,
        estimate_id=estimate.id,
        verdict=reply.verdict,
        summary=reply.summary,
        flags=[f.model_dump(mode="json") for f in reply.flags],
        model=result.model,
        prompt_version=rules.second_opinion_prompt,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    return _out(row)
