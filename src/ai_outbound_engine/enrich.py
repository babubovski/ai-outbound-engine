"""Optional homepage enrichment: fetch a company's site and reduce it to plain text."""

from __future__ import annotations

import re
from html.parser import HTMLParser

import requests

USER_AGENT = "Mozilla/5.0 (compatible; ai-outbound-engine/0.1)"
_SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.meta: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag == "meta":
            a = dict(attrs)
            if (a.get("name") or a.get("property") or "").lower() in {"description", "og:description"}:
                self.meta.append(a.get("content") or "")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth and data.strip():
            self.parts.append(data.strip())


def html_to_text(html: str, max_chars: int = 2000) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = " ".join(dict.fromkeys(parser.meta + parser.parts))  # dedupe, keep order
    return re.sub(r"\s+", " ", text).strip()[:max_chars]


class HomepageFetcher:
    """Fetches each domain once per run. Any failure returns an empty string, never raises."""

    def __init__(self, timeout: float = 6.0, max_chars: int = 2000) -> None:
        self.timeout = timeout
        self.max_chars = max_chars
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._cache: dict[str, str] = {}

    def __call__(self, domain: str) -> str:
        if domain not in self._cache:
            self._cache[domain] = self._fetch(domain)
        return self._cache[domain]

    def _fetch(self, domain: str) -> str:
        url = domain if domain.startswith("http") else f"https://{domain}"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException:
            return ""
        if "html" not in resp.headers.get("content-type", ""):
            return ""
        return html_to_text(resp.text, self.max_chars)
