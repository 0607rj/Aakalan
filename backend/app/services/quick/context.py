"""What the review and results pages say about the project (OPEN_QUESTIONS 205): the industry
the AI read (shown only), the project type and the user roles, worked out in code, and the
prerequisite warnings. None of it reaches the engine: it never changes a price or a seed.
"""

import re

from pydantic import BaseModel

from app.services.quick.config import QuickConfig

# the story format the readers and the story drafter are asked for: "As a <role>, I can ..."
_ROLE = re.compile(r"^\s*as\s+(?:an?|the)\s+(.+?)\s*,", re.IGNORECASE)


class ProjectContext(BaseModel):
    domain: str = ""  # the industry, as the AI read it ("" when not read or not clear)
    project_type: str
    user_roles: list[str] = []


class Prerequisite(BaseModel):
    """A feature, or an add-on the document asks for, that usually needs a feature not ticked."""

    key: str  # the feature or add-on asking
    label: str
    needs: list[str]  # labels of the features, any one of which would do
    why: str


def user_roles(stories: list[str], limit: int) -> list[str]:
    """The roles named in the stories, in first-seen order, each once (any case)."""
    out: dict[str, str] = {}
    for story in stories:
        hit = _ROLE.match(story)
        if hit:
            role = " ".join(hit.group(1).split())
            out.setdefault(role.lower(), role[:1].upper() + role[1:])
    return list(out.values())[:limit]


def project_type(cfg: QuickConfig, features: list[str]) -> str:
    """The configured project type sharing most features with the ticked ones (the first in
    the config's order on a tie), with the mobile-app note when the app is ticked."""
    rules = cfg.project_context
    chosen = set(features)
    best, best_score = None, 0
    for t in cfg.project_types:
        score = len(chosen & set(t.features))
        if score > best_score:
            best, best_score = t, score
    other = rules.other_type if rules else ""
    label = best.label if best else other
    if rules and "mobile_app" in chosen:
        label = f"{label}, {rules.mobile_app_note}"
    return label


def missing_prerequisites(
    cfg: QuickConfig,
    features: list[str],
    asked_scope: list[str] | None = None,
    answered: dict[str, str] | None = None,
) -> list[Prerequisite]:
    """Warnings, each once: a ticked feature whose rule needs a feature not ticked, and an
    add-on asked for (`asked_scope`, e.g. found in the document) whose feature is not ticked.
    A rule is skipped when a question it names was answered (`answered`: by the document or
    the user, not a default) with a value it names. Nothing is added to the estimate."""
    given = {k: str(v) for k, v in (answered or {}).items()}
    rules = cfg.project_context
    chosen = set(features)
    labels = {f.key: f.label for f in cfg.features}
    out: dict[str, Prerequisite] = {}
    for rule in rules.prerequisites if rules else []:
        if any(given.get(q) in values for q, values in rule.not_when_answered.items()):
            continue
        if rule.feature in chosen and not chosen & set(rule.needs_any):
            out[rule.feature] = Prerequisite(
                key=rule.feature,
                label=labels.get(rule.feature, rule.feature),
                needs=[labels.get(k, k) for k in rule.needs_any],
                why=rule.why,
            )
    for group in cfg.scope:
        if group.feature is None or group.feature in chosen:
            continue
        for item in group.items:
            if item.key in (asked_scope or []) and item.key not in out:
                feature = labels.get(group.feature, group.feature)
                out[item.key] = Prerequisite(
                    key=item.key,
                    label=item.label,
                    needs=[feature],
                    why=f"Asked for, but it adds to {feature}, which is not ticked, so it is "
                    "not in the price.",
                )
    return list(out.values())
