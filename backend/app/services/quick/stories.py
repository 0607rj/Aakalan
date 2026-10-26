"""User stories drafted by the AI when a project has no document (OPEN_QUESTIONS 164), so the
story-size check (size_check.py) also works for a typed-in feature list.

The AI only suggests text (rule 1): the user's description and the feature names are fenced
as data (rule 7), the reply is validated and trimmed in code, and the user edits and confirms
the stories on the form before they are used (rule 6). Drafted stories feed the size check
only; a feature's level and every price stay as the user chose them. Nothing is stored here.
"""

import logging

from pydantic import BaseModel, Field

from app.llm.client import LLMNotConfiguredError, LLMRefusedError, get_llm_client, load_prompt
from app.services.quick.config import SizeCheck

log = logging.getLogger(__name__)


class StoryFeature(BaseModel):
    key: str = Field(max_length=200)  # a feature key, or a custom feature's name
    label: str = Field(max_length=300)


class DraftIn(BaseModel):
    description: str = Field(default="", max_length=4000)
    features: list[StoryFeature] = Field(min_length=1, max_length=60)


class _DraftedFeature(BaseModel):
    key: str
    stories: list[str] = []


class _Reply(BaseModel):
    features: list[_DraftedFeature] = []


class DraftOut(BaseModel):
    available: bool
    stories: dict[str, list[str]] = {}  # feature key -> drafted stories
    note: str | None = None  # why nothing was drafted


NO_KEY = "No AI key is set up, so stories can't be drafted. You can write them yourself or skip."
FAILED = "The AI could not draft stories just now. You can write them yourself or skip."


def fenced(text: str, tag: str) -> str:
    """The user's text between <tag> and </tag>, with any closing tag inside it broken."""
    return f"<{tag}>\n{text.replace(f'</{tag}>', f'</ {tag}>')}\n</{tag}>"


def clean(reply: _Reply, keys: set[str], rules: SizeCheck) -> dict[str, list[str]]:
    """Stories for the features asked about only: trimmed, without repeats (any case), at most
    `draft_max_stories` each, each at most `draft_max_chars`."""
    out: dict[str, list[str]] = {}
    seen: set[str] = set()
    for f in reply.features:
        if f.key not in keys:
            continue
        for story in f.stories:
            text = " ".join(story.split())
            low = text.lower()
            if not text or len(text) > rules.draft_max_chars or low in seen:
                continue
            stories = out.setdefault(f.key, [])
            if len(stories) < rules.draft_max_stories:
                seen.add(low)
                stories.append(text)
    return out


def draft_stories(rules: SizeCheck, body: DraftIn) -> DraftOut:
    """Ask the AI for each feature's user stories (module docstring)."""
    try:
        llm = get_llm_client()
    except LLMNotConfiguredError:
        return DraftOut(available=False, note=NO_KEY)
    system = (
        load_prompt(f"{rules.draft_prompt}.md")
        .replace("{{max_stories}}", str(rules.draft_max_stories))
        .replace("{{max_chars}}", str(rules.draft_max_chars))
    )
    listed = "\n".join(f"- {f.key}: {f.label}" for f in body.features)
    user = f"{fenced(body.description.strip(), 'description')}\n{fenced(listed, 'features')}"
    try:
        reply = llm.extract(system=system, user=user, schema=_Reply).output
    except LLMRefusedError:
        return DraftOut(available=False, note=FAILED)
    except Exception:  # network / API errors: the user can still write or skip
        log.exception("drafting user stories failed")
        return DraftOut(available=False, note=FAILED)
    return DraftOut(available=True, stories=clean(reply, {f.key for f in body.features}, rules))
