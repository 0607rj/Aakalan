"""Opening a source page to check a figure: public http(s) pages only (never private, loopback
or link-local addresses, so a URL from the AI cannot reach internal systems), a few redirects,
a time and size limit, and the visible text of the HTML. Nothing from the tender is sent: only
a GET of the public URL."""

import ipaddress
import socket
import urllib.error
import urllib.request
from collections.abc import Callable
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

MAX_REDIRECTS = 3
USER_AGENT = "Aakalan-source-check/1.0"


class FetchError(RuntimeError):
    """The page could not be opened safely."""


def _public_host(url: str) -> None:
    parts = urlparse(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise FetchError(f"not a web address: {url}")
    if "." not in parts.hostname:
        raise FetchError(f"not a public host: {parts.hostname}")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or None, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise FetchError(f"host not found: {parts.hostname}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise FetchError(f"not a public address: {parts.hostname}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None  # redirects are followed by hand, each target checked first


_OPENER = urllib.request.build_opener(_NoRedirect)


class _Text(HTMLParser):
    SKIP = frozenset({"script", "style", "noscript", "svg", "head"})

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_text(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    return " ".join(parser.parts)


def fetch_text(url: str, timeout: int, max_bytes: int) -> str:
    """The page's visible text."""
    for _ in range(MAX_REDIRECTS + 1):
        _public_host(url)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with _OPENER.open(request, timeout=timeout) as response:
                body = response.read(max_bytes + 1)
                charset = response.headers.get_content_charset() or "utf-8"
                kind = response.headers.get_content_type()
        except urllib.error.HTTPError as exc:
            location = exc.headers.get("Location") if 300 <= exc.code < 400 else None
            if location:
                url = urljoin(url, location)
                continue
            raise FetchError(f"HTTP {exc.code}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise FetchError(str(exc)) from exc
        if len(body) > max_bytes:
            raise FetchError("page too large")
        text = body.decode(charset, errors="replace")
        return html_text(text) if "html" in kind else text
    raise FetchError("too many redirects")


PageFetcher = Callable[[str, int, int], str]
_override: PageFetcher | None = None


def set_page_fetcher(fetcher: PageFetcher | None) -> None:
    """Install a fetcher (tests); None restores real fetching."""
    global _override
    _override = fetcher


def get_page_fetcher() -> PageFetcher:
    return _override or fetch_text
