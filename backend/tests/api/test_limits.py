"""Limits against abuse (services/limits.py, OPEN_QUESTIONS 190): sign-ups and contact
messages per caller address, AI calls per company a day. Off for the rest of the suite."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.llm.client import FakeClient, set_llm_client
from app.models import RateEvent
from app.services import limits
from app.services.email import set_email_sender

H = dict[str, str]


class _Quiet:
    def send(self, to: str, subject: str, body: str, html: str | None = None) -> None:
        self.body = body


@pytest.fixture
def clean(db: Session) -> Iterator[Session]:
    db.execute(delete(RateEvent))
    db.commit()
    yield db
    db.execute(delete(RateEvent))
    db.commit()


def test_sign_ups_from_one_address_are_limited(
    client: TestClient, clean: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "signup_ip_max_per_hour", 2)
    box = _Quiet()
    set_email_sender(box)
    try:
        codes = []
        for i in range(3):
            body = {"full_name": "Spam <a href=x>", "email": f"s{i}@limit.example",
                    "password": "long-enough-1"}  # fmt: skip
            codes.append(client.post("/auth/signup", json=body))
        assert [r.status_code for r in codes] == [201, 201, 429]
        assert "Retry-After" in codes[2].headers
        assert "Spam" not in box.body  # the typed name never goes into the email
    finally:
        set_email_sender(None)


def test_contact_messages_from_one_address_are_limited(
    client: TestClient, clean: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "contact_ip_max_per_hour", 1)
    body = {"name": "Asha", "email": "asha@limit.example", "message": "Hello there"}
    assert client.post("/contact", json=body).status_code == 201
    assert client.post("/contact", json=body).status_code == 429


def test_ai_calls_stop_at_the_company_limit(
    client: TestClient, admin_headers: H, clean: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Past the day's AI calls nothing more is sent to the AI: drafted stories say so."""
    monkeypatch.setattr(get_settings(), "ai_org_max_per_day", 1)

    def never(system: str, user: str) -> object:
        raise AssertionError("the AI was called past the limit")

    set_llm_client(FakeClient(never))
    try:
        me = client.get("/auth/me", headers=admin_headers).json()
        limits.record_ai(clean, me["org_id"])
        clean.commit()
        body = {"features": [{"key": "online_forms", "label": "Online forms"}]}
        r = client.post("/quick-estimate/draft-stories", json=body, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["available"] is False and "today" in r.json()["note"]
    finally:
        set_llm_client(None)


def test_viewers_start_no_ai_calls(client: TestClient, viewer_headers: H) -> None:
    body = {"features": [{"key": "online_forms", "label": "Online forms"}]}
    r = client.post("/quick-estimate/draft-stories", json=body, headers=viewer_headers)
    assert r.status_code == 403
    text = {"text": "A portal where citizens register and pay fees."}
    assert (
        client.post("/quick-estimate/suggest", json=text, headers=viewer_headers).status_code == 403
    )


def test_settings_hide_the_margin_from_other_roles(
    client: TestClient, estimator_headers: H, admin_headers: H
) -> None:
    old = client.get("/settings", headers=admin_headers).json()
    try:
        r = client.put("/settings", json={**old, "margin_percent": "0.15"}, headers=admin_headers)
        assert r.status_code == 200
        assert client.get("/settings", headers=admin_headers).json()["margin_percent"] == "0.15"
        assert client.get("/settings", headers=estimator_headers).json()["margin_percent"] is None
    finally:
        client.put("/settings", json=old, headers=admin_headers)
