"""Reality checks on the summary, and the AI second opinion (fake AI only)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.llm.client import FakeClient, set_llm_client

H = dict[str, str]


@pytest.fixture
def no_fake() -> Iterator[None]:
    yield
    set_llm_client(None)


def todo_app(client: TestClient, headers: H) -> Any:
    body = {
        "name": "To-do app",
        "features": [],
        "custom_features": [{"name": "To-do list", "category": "module", "size": "S"}],
        "choices": {"version": "mvp", "support_years": 0},
    }
    r = client.post("/quick-estimates", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_tiny_app_is_flagged(client: TestClient, admin_headers: H) -> None:
    s = todo_app(client, admin_headers)
    reality = s["reality"]
    assert reality["verdict"] == "check"
    setup = next(c for c in reality["checks"] if c["key"] == "setup_share")
    assert not setup["ok"] and "set-up" in setup["title"].lower()


def test_second_opinion_without_key(client: TestClient, admin_headers: H) -> None:
    s = todo_app(client, admin_headers)
    url = f"/estimates/{s['estimate_id']}/second-opinion"
    assert client.get(url, headers=admin_headers).json() == {
        "ai_available": False,
        "opinion": None,
    }
    assert client.post(url, headers=admin_headers).status_code == 409


def test_second_opinion_drops_numbers(client: TestClient, admin_headers: H, no_fake: None) -> None:
    seen: list[str] = []

    def respond(system: str, user: str) -> object:
        seen.append(user)
        return {
            "verdict": "check",
            "summary": "Mostly fine.",
            "flags": [
                {"kind": "level_too_high", "feature": "To-do list", "message": "Basic is enough."},
                {"kind": "other", "feature": None, "message": "Should cost 2 lakh."},
                {"kind": "missing", "feature": "Not a feature", "message": "Add an admin panel."},
            ],
        }

    s = todo_app(client, admin_headers)  # before the fake AI, so nothing is researched
    set_llm_client(FakeClient(respond))
    url = f"/estimates/{s['estimate_id']}/second-opinion"
    r = client.post(url, headers=admin_headers)
    assert r.status_code == 200, r.text
    opinion = r.json()["opinion"]
    assert opinion["verdict"] == "check"
    assert [f["message"] for f in opinion["flags"]] == ["Basic is enough.", "Add an admin panel."]
    assert opinion["flags"][1]["feature"] is None  # not a feature of this estimate
    assert seen[0].startswith("<estimate>") and "To-do list" in seen[0]
    got = client.get(url, headers=admin_headers).json()
    assert got["opinion"]["flags"] == opinion["flags"]
    client.post(url, headers=admin_headers)  # asking again replaces it
    assert len(client.get(url, headers=admin_headers).json()["opinion"]["flags"]) == 2
