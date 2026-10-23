"""Sign-up, email verification, password reset and change: emailed 6-digit codes and JWT
token versions. Emails go to a fake mailbox."""

import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.email import set_email_sender

H = dict[str, str]


class Mailbox:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))

    def code(self, to: str) -> str:
        body = next(b for t, _, b in reversed(self.sent) if t == to)
        found = re.search(r"\b(\d{6})\b", body)
        assert found is not None
        return found.group(1)


@pytest.fixture
def mail(monkeypatch: pytest.MonkeyPatch) -> Iterator[Mailbox]:
    box = Mailbox()
    set_email_sender(box)
    monkeypatch.setattr(get_settings(), "otp_resend_seconds", 0)
    yield box
    set_email_sender(None)


def bearer(token: str) -> H:
    return {"Authorization": f"Bearer {token}"}


def signup(client: TestClient, email: str, company: str, password: str = "long-enough-1") -> int:
    body = {"full_name": "Asha", "company": company, "email": email, "password": password}
    return client.post("/auth/signup", json=body).status_code


def test_signup_verify_and_sign_in(client: TestClient, mail: Mailbox) -> None:
    assert signup(client, "Asha@Newco.example", "Newco Systems") == 201
    login = {"email": "asha@newco.example", "password": "long-enough-1"}
    r = client.post("/auth/login", json=login)
    assert r.status_code == 403 and r.json()["detail"] == "Email not verified"
    wrong = client.post("/auth/verify-email", json={"email": login["email"], "code": "000000"})
    assert wrong.status_code == 400
    code = mail.code("asha@newco.example")
    ok = client.post("/auth/verify-email", json={"email": login["email"], "code": code})
    assert ok.status_code == 200
    me = client.get("/auth/me", headers=bearer(ok.json()["access_token"])).json()
    assert (me["org_name"], me["role"]) == ("Newco Systems", "admin")
    again = client.post("/auth/verify-email", json={"email": login["email"], "code": code})
    assert again.status_code == 400  # a code works once
    assert client.post("/auth/login", json=login).status_code == 200
    # the new company sees none of the demo company's estimates
    token = client.post("/auth/login", json=login).json()["access_token"]
    assert client.get("/quick-estimates", headers=bearer(token)).json() == []


def test_signup_with_name_email_and_password_only(client: TestClient, mail: Mailbox) -> None:
    body = {"full_name": "Ravi", "email": "ravi@solo.example", "password": "long-enough-1"}
    assert client.post("/auth/signup", json=body).status_code == 201
    code = mail.code("ravi@solo.example")
    ok = client.post("/auth/verify-email", json={"email": "ravi@solo.example", "code": code})
    me = client.get("/auth/me", headers=bearer(ok.json()["access_token"])).json()
    assert (me["full_name"], me["org_name"], me["role"]) == ("Ravi", "ravi@solo.example", "admin")


def test_signup_refusals(client: TestClient, mail: Mailbox) -> None:
    assert signup(client, "taken@newco.example", "Taken Co") == 201
    code = mail.code("taken@newco.example")
    client.post("/auth/verify-email", json={"email": "taken@newco.example", "code": code})
    assert signup(client, "taken@newco.example", "Other Co") == 409  # verified account
    assert signup(client, "someone@else.example", "taken co") == 409  # company name in use
    assert signup(client, "short@newco.example", "Short Co", password="short") == 422
    assert signup(client, "not-an-email", "Bad Co") == 422
    # not verified yet: signing up again sends a new code
    assert signup(client, "pending@newco.example", "Pending Co") == 201
    assert signup(client, "pending@newco.example", "Pending Co") == 201
    assert len([t for t, _, _ in mail.sent if t == "pending@newco.example"]) == 2


def test_forgot_and_reset_password(client: TestClient, mail: Mailbox) -> None:
    assert signup(client, "reset@newco.example", "Reset Co") == 201
    v = client.post(
        "/auth/verify-email",
        json={"email": "reset@newco.example", "code": mail.code("reset@newco.example")},
    )
    old = v.json()["access_token"]
    unknown = client.post("/auth/password/forgot", json={"email": "nobody@x.example"})
    known = client.post("/auth/password/forgot", json={"email": "reset@newco.example"})
    assert unknown.status_code == known.status_code == 200
    assert "nobody@x.example" not in [t for t, _, _ in mail.sent]  # no hint either way
    body = {"email": "reset@newco.example", "code": "123", "new_password": "brand-new-pass"}
    assert client.post("/auth/password/reset", json=body).status_code == 400
    body["code"] = mail.code("reset@newco.example")
    r = client.post("/auth/password/reset", json=body)
    assert r.status_code == 200
    assert client.get("/auth/me", headers=bearer(old)).status_code == 401  # signed out
    assert client.get("/auth/me", headers=bearer(r.json()["access_token"])).status_code == 200
    login = {"email": "reset@newco.example", "password": "brand-new-pass"}
    assert client.post("/auth/login", json=login).status_code == 200


def test_a_code_stops_after_too_many_tries(client: TestClient, mail: Mailbox) -> None:
    assert signup(client, "tries@newco.example", "Tries Co") == 201
    code = mail.code("tries@newco.example")
    for _ in range(get_settings().otp_max_attempts):
        bad = client.post("/auth/verify-email", json={"email": "tries@newco.example", "code": "1"})
        assert bad.status_code == 400
    late = client.post("/auth/verify-email", json={"email": "tries@newco.example", "code": code})
    assert late.status_code == 400
    resend = client.post("/auth/verify-email/resend", json={"email": "tries@newco.example"})
    assert resend.status_code == 200
    fresh = mail.code("tries@newco.example")
    ok = client.post("/auth/verify-email", json={"email": "tries@newco.example", "code": fresh})
    assert ok.status_code == 200


def test_resend_waits(client: TestClient, mail: Mailbox, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "otp_resend_seconds", 60)
    assert signup(client, "wait@newco.example", "Wait Co") == 201
    r = client.post("/auth/verify-email/resend", json={"email": "wait@newco.example"})
    assert r.status_code == 429 and "seconds" in r.json()["detail"]


def test_change_password(client: TestClient, mail: Mailbox) -> None:
    assert signup(client, "change@newco.example", "Change Co") == 201
    v = client.post(
        "/auth/verify-email",
        json={"email": "change@newco.example", "code": mail.code("change@newco.example")},
    )
    old = v.json()["access_token"]
    wrong = {"current_password": "nope", "new_password": "another-pass-2"}
    assert client.post("/auth/password/change", json=wrong, headers=bearer(old)).status_code == 400
    body = {"current_password": "long-enough-1", "new_password": "another-pass-2"}
    r = client.post("/auth/password/change", json=body, headers=bearer(old))
    assert r.status_code == 200
    assert client.get("/auth/me", headers=bearer(old)).status_code == 401
    assert client.get("/auth/me", headers=bearer(r.json()["access_token"])).status_code == 200
