"""The same description gives the same features on every "Find features" click: the AI's
reading is kept per organisation by a fingerprint of the text (OPEN_QUESTIONS 181)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.client import FakeClient, set_llm_client
from app.models import DescriptionReading

H = dict[str, str]
TEXT = "A clinic site where patients book appointments and pay the fee online."
OTHER = "A clinic site where patients book appointments and get an SMS reminder."
BOOK = {
    "key": "bookings",
    "evidence": [{"page": 1, "clause_ref": "", "quote": "patients book appointments"}],
}
PAY = {
    "key": "payments",
    "evidence": [{"page": 1, "clause_ref": "", "quote": "pay the fee online"}],
}


def test_same_words_give_the_same_features(
    client: TestClient, admin_headers: H, db: Session
) -> None:
    calls = []

    def responder(system: str, user: str) -> object:
        """An AI that answers differently each time it is asked."""
        calls.append(user)
        found = [BOOK, PAY] if len(calls) % 2 else [BOOK]
        return {
            "project_name": "", "summary": "", "features": found, "other_features": [],
            "choices": [], "numbers": [], "unclear_points": [],
        }  # fmt: skip

    def suggest(text: str) -> list[str]:
        r = client.post("/quick-estimate/suggest", json={"text": text}, headers=admin_headers)
        assert r.status_code == 200, r.text
        assert r.json()["reader"] == "ai"
        return sorted(f["key"] for f in r.json()["features"])

    set_llm_client(FakeClient(responder))
    try:
        first = suggest(TEXT)
        asked = len(calls)
        assert asked > 0
        for _ in range(3):
            assert suggest(TEXT) == first
        assert len(calls) == asked  # kept: the AI is not asked again
        suggest(OTHER)
        assert len(calls) > asked  # other words are read afresh
    finally:
        set_llm_client(None)
    rows = db.scalars(select(DescriptionReading)).all()
    assert len(rows) == 2
    assert all(len(r.text_sha256) == 64 for r in rows)
