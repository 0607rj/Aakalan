"""Every email the app sends, in one look (OPEN_QUESTIONS 223): a plain-text copy and an HTML copy
built from the same parts, so the two always say the same thing. The HTML uses tables and
inline styles only, which is what mail apps (Gmail, Outlook, Apple Mail) render reliably; the
colours are the app's own (frontend `globals.css`: ink, orange, page, border).

Nothing a person typed goes into an email (anyone can sign up with any address), and every part
is HTML-escaped."""

import re
from dataclasses import dataclass
from html import escape

from app.core.config import get_settings

INK = "#111110"
EMBER = "#c2500f"
ORANGE = "#c94210"
PAGE = "#f6f6f3"
BORDER = "#e3e3dc"
TEXT = "#141414"
MUTED = "#66665f"
CODE_BG = "#fdf1ea"
GRID = "rgba(255,255,255,0.07)"  # the header's faint grid lines
GRID_CELL = "22px"
FONT = "'Google Sans Flex', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
MONO = "'IBM Plex Mono', Consolas, 'Courier New', monospace"
FOOTER = (
    "Aakalan · software cost estimates. This mailbox is not read; to reach us, use the "
    "Contact page."
)


@dataclass(frozen=True)
class Email:
    subject: str
    text: str
    html: str


def site_link(path: str) -> str:
    """A full link into the web app: `site_url`, or else the first allowed web origin."""
    s = get_settings()
    base = s.site_url or (s.cors_origins[0] if s.cors_origins else "")
    return f"{base.rstrip('/')}{path}"


def compose(
    subject: str,
    heading: str,
    paragraphs: list[str],
    *,
    preview: str = "",
    code: str | None = None,
    code_note: str = "",
    button: tuple[str, str] | None = None,
    footnote: str = "",
) -> Email:
    """One email: a heading, a few short paragraphs, then optionally a big code to copy (with a
    note under it, e.g. how long it works) or one button (label, link), and a small footnote."""
    text = [heading, "", *_spaced(paragraphs)]
    if code is not None:
        text += ["", f"    {code}", ""]
        if code_note:
            text += [code_note, ""]
    if button is not None:
        text += ["", f"{button[0]}: {button[1]}", ""]
    if footnote:
        text += ["", footnote]
    text += ["", "Aakalan", "", FOOTER]
    plain = re.sub(r"\n{3,}", "\n\n", "\n".join(text)).strip() + "\n"
    return Email(subject=subject, text=plain, html=_html(
        subject, heading, paragraphs, preview, code, code_note, button, footnote
    ))  # fmt: skip


def _spaced(paragraphs: list[str]) -> list[str]:
    out: list[str] = []
    for p in paragraphs:
        out += [p, ""]
    return out[:-1]


def _html(
    subject: str,
    heading: str,
    paragraphs: list[str],
    preview: str,
    code: str | None,
    code_note: str,
    button: tuple[str, str] | None,
    footnote: str,
) -> str:
    body = "".join(
        f'<p style="margin:0 0 14px;font-size:15px;line-height:1.6;color:{TEXT};">{escape(p)}</p>'
        for p in paragraphs
    )
    if code is not None:
        body += (
            f'<div style="margin:22px 0 8px;padding:18px 12px;background:{CODE_BG};'
            f"border:1px solid #f3cdb8;border-radius:12px;text-align:center;font-family:{MONO};"
            f"font-size:34px;font-weight:700;letter-spacing:10px;color:{ORANGE};"
            f'">{escape(code)}</div>'
        )
        if code_note:
            body += (
                f'<p style="margin:0 0 14px;font-size:13px;color:{MUTED};text-align:center;">'
                f"{escape(code_note)}</p>"
            )
    if button is not None:
        label, link = button
        body += (
            '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0 8px;">'
            f'<tr><td style="border-radius:10px;background:{ORANGE};">'
            f'<a href="{escape(link, quote=True)}" style="display:inline-block;padding:12px 24px;'
            f"font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;"
            f'border-radius:10px;">{escape(label)}</a></td></tr></table>'
        )
    if footnote:
        body += (
            f'<p style="margin:22px 0 0;padding-top:16px;border-top:1px solid {BORDER};'
            f'font-size:13px;line-height:1.55;color:{MUTED};">{escape(footnote)}</p>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="light"><meta name="supported-color-schemes" '
        f'content="light"><title>{escape(subject)}</title></head>'
        f'<body style="margin:0;padding:0;background:{PAGE};">'
        # the line mail apps show beside the subject, hidden in the email itself
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;">'
        f"{escape(preview or heading)}</div>"
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{PAGE};font-family:{FONT};"><tr><td align="center" '
        'style="padding:32px 16px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="max-width:520px;">'
        # the ink header with the ember glow, as in the app's sidebar, and a faint grid as
        # behind the app's page titles (`.app-head-grid`); a mail app without gradients shows
        # plain ink
        f'<tr><td style="background-color:{INK};background-image:'
        f"linear-gradient(to right,{GRID} 1px,transparent 1px),"
        f"linear-gradient(to bottom,{GRID} 1px,transparent 1px),"
        f"radial-gradient(120% 140% at 0% 0%,{EMBER} 0%,{INK} 62%);"
        f"background-size:{GRID_CELL} {GRID_CELL},{GRID_CELL} {GRID_CELL},100% 100%;"
        "background-position:-1px -1px,-1px -1px,0 0;"
        'border-radius:16px 16px 0 0;padding:26px 28px;">'
        f'<span style="font-size:20px;font-weight:700;letter-spacing:-0.2px;color:#ffffff;">'
        f'Aakalan</span><span style="color:{ORANGE};font-size:20px;font-weight:700;">.</span>'
        "</td></tr>"
        f'<tr><td style="background:#ffffff;border:1px solid {BORDER};border-top:0;'
        'border-radius:0 0 16px 16px;padding:30px 28px 28px;">'
        f'<h1 style="margin:0 0 16px;font-size:22px;line-height:1.3;font-weight:700;'
        f'color:{TEXT};">{escape(heading)}</h1>{body}</td></tr>'
        f'<tr><td style="padding:18px 8px 0;font-size:12px;line-height:1.5;color:{MUTED};'
        f'text-align:center;">{escape(FOOTER)}</td></tr>'
        "</table></td></tr></table></body></html>"
    )


# --- the emails --------------------------------------------------------------------------------


def code_email(purpose: str, code: str, minutes: int) -> Email:
    """The 6-digit code to confirm an email address or reset a password. The code is in the
    subject too, so it shows in the phone's notification."""
    works = f"The code works for {minutes} minutes and can be used once."
    if purpose == "reset_password":
        return compose(
            f"{code} is your Aakalan password reset code",
            "Reset your password",
            [
                "Someone asked to reset the password of the Aakalan account for this email "
                "address. Enter this code on the reset page to choose a new password:"
            ],
            preview=f"Your code is {code}. It works for {minutes} minutes.",
            code=code,
            code_note=works,
            footnote="Did not ask for this? You can ignore this email: your password stays "
            "the same, and nobody can change it without the code.",
        )
    return compose(
        f"{code} is your Aakalan verification code",
        "Confirm your email address",
        [
            "Welcome to Aakalan. To finish creating your account, enter this code on the "
            "sign-up page:"
        ],
        preview=f"Your code is {code}. It works for {minutes} minutes.",
        code=code,
        code_note=works,
        footnote="Did not sign up for Aakalan? You can ignore this email: no account is "
        "made without the code.",
    )


def account_off_email() -> Email:
    return compose(
        "Your Aakalan account has been turned off",
        "Your account has been turned off",
        [
            "The Aakalan team has turned off the account for this email address, so it can "
            "no longer sign in.",
            "Your estimates are kept: nothing is lost if the account is turned on again.",
        ],
        button=("Contact us", site_link("/contact")),
        footnote="If you think this is a mistake, write to us from the Contact page and we "
        "will look into it.",
    )


def account_on_email() -> Email:
    return compose(
        "Your Aakalan account is on again",
        "Welcome back",
        [
            "Your Aakalan account has been turned on again. You can sign in as before, and your "
            "estimates are where you left them."
        ],
        button=("Sign in", site_link("/login")),
    )


def account_deleted_email(with_company: bool) -> Email:
    what = (
        "Your Aakalan account has been deleted, together with its estimates and uploaded "
        "documents. This cannot be undone."
        if with_company
        else "Your Aakalan account has been deleted. Your company's estimates stay with its "
        "other members."
    )
    return compose(
        "Your Aakalan account has been deleted",
        "Your account has been deleted",
        [what, "You are welcome to create a new account at any time."],
        button=("Contact us", site_link("/contact")),
        footnote="If you think this is a mistake, write to us from the Contact page.",
    )


def test_email() -> Email:
    return compose(
        "Aakalan test email",
        "Email works",
        [
            "This is a test email from Aakalan. If you can read it, the email (SMTP) settings "
            "are right and sign-up codes will arrive."
        ],
    )
