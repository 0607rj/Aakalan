"""Sending email behind one small interface, so the transport is a config change (rule 9):
SMTP when `smtp_host` is set; otherwise, outside production, the message is written to the
server log (development: the sign-up and reset codes appear there). Tests install a fake."""

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.core.config import get_settings

log = logging.getLogger(__name__)


class EmailNotConfiguredError(RuntimeError):
    """No way to send email (production without SMTP), or the SMTP server refused it."""


class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class SmtpSender:
    def send(self, to: str, subject: str, body: str) -> None:
        s = get_settings()
        msg = EmailMessage()
        msg["From"] = s.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        try:
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as smtp:
                if s.smtp_starttls:
                    smtp.starttls()
                if s.smtp_username:
                    smtp.login(s.smtp_username, s.smtp_password)
                smtp.send_message(msg)
        except (OSError, smtplib.SMTPException) as exc:  # wrong password, server down, ...
            log.error("email to %s not sent: %s", to, exc)
            raise EmailNotConfiguredError("The email could not be sent") from exc


class LogSender:
    """Development only: the email in the server log instead of a mailbox."""

    def send(self, to: str, subject: str, body: str) -> None:
        log.warning("EMAIL (not sent, no SMTP configured) to %s: %s\n%s", to, subject, body)


_override: EmailSender | None = None


def set_email_sender(sender: EmailSender | None) -> None:
    global _override
    _override = sender


def get_email_sender() -> EmailSender:
    if _override is not None:
        return _override
    s = get_settings()
    # a username without its password (the .env placeholder) is not set up yet
    if s.smtp_host and (s.smtp_password or not s.smtp_username):
        return SmtpSender()
    if s.environment == "production":
        raise EmailNotConfiguredError("Email is not set up (SMTP_HOST)")
    return LogSender()
