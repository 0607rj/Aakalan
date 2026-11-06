"""OPEN_QUESTIONS 223: every email has a plain-text and an HTML copy that say the same thing;
the code is in the subject; links point at the web app (`site_url`)."""

import pytest

from app.core.config import get_settings
from app.services import email_templates as t


def test_the_code_is_in_the_subject_the_text_and_a_big_box() -> None:
    for purpose in ("verify_email", "reset_password"):
        mail = t.code_email(purpose, "482913", 10)
        assert mail.subject.startswith("482913 is your Aakalan")
        assert "482913" in mail.text and "10 minutes" in mail.text
        assert ">482913</div>" in mail.html and "<!doctype html>" in mail.html
    assert "Reset your password" in t.code_email("reset_password", "1", 10).html
    assert "Confirm your email address" in t.code_email("verify_email", "1", 10).html


def test_every_email_has_both_copies_and_the_same_heading() -> None:
    for mail in (
        t.account_off_email(),
        t.account_on_email(),
        t.account_deleted_email(with_company=True),
        t.account_deleted_email(with_company=False),
        t.test_email(),
    ):
        heading = mail.text.splitlines()[0]
        assert f">{heading}</h1>" in mail.html
        assert "\n\n\n" not in mail.text


def test_links_point_at_the_web_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "site_url", "https://aakalan.example/")
    off = t.account_off_email()
    assert 'href="https://aakalan.example/contact"' in off.html
    assert "Contact us: https://aakalan.example/contact" in off.text
    monkeypatch.setattr(get_settings(), "site_url", "")
    monkeypatch.setattr(get_settings(), "cors_origins", ["http://localhost:3000"])
    assert t.site_link("/login") == "http://localhost:3000/login"


def test_text_is_escaped_in_the_html() -> None:
    mail = t.compose("S", "A <b> & c", ["1 < 2"], button=("Go", 'https://x/?a="b"'))
    assert "A &lt;b&gt; &amp; c" in mail.html and "1 &lt; 2" in mail.html
    assert 'href="https://x/?a=&quot;b&quot;"' in mail.html
