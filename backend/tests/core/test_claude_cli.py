"""LLM_PROVIDER=claude_cli (development only, OPEN_QUESTIONS 234): the local `claude` command
in print mode, never billed to the API key, no tools while reading, the reply checked against
the schema. The command is stubbed here: no AI is called."""

import json
import subprocess
from typing import Any

import pytest
from pydantic import BaseModel

from app.core.config import get_settings
from app.llm import client as llm


class Answer(BaseModel):
    ok: bool


def test_runs_the_cli_without_the_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, Any]] = []
    replies = iter(["not json at all", '{"ok": true}'])

    def run(command: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
        seen.append({"command": command, **kw})
        body = {"result": next(replies), "usage": {"input_tokens": 3, "output_tokens": 2},
                "modelUsage": {"claude-sonnet-5-5": {}}}  # fmt: skip
        return subprocess.CompletedProcess(command, 0, json.dumps(body), "")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-be-used")
    monkeypatch.setattr("shutil.which", lambda _: "claude")
    monkeypatch.setattr(subprocess, "run", run)
    out = llm.ClaudeCliClient(get_settings()).extract(system="s", user="u", schema=Answer)
    assert out.output.ok and out.model == "claude-sonnet-5-5 (claude CLI)"
    assert len(seen) == 2  # invalid JSON asked for again
    first = seen[0]
    assert "ANTHROPIC_API_KEY" not in first["env"]
    assert first["command"][first["command"].index("--tools") + 1] == ""  # no tools
    assert first["input"] == "u"


def test_chosen_by_the_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "claude_cli")
    monkeypatch.setattr("shutil.which", lambda _: "claude")
    get_settings.cache_clear()
    try:
        assert isinstance(llm.get_llm_client(), llm.ClaudeCliClient)
    finally:
        monkeypatch.delenv("LLM_PROVIDER")
        get_settings.cache_clear()
