"""Post-processing guardrails applied to every generated string, whichever generator wrote it."""

from __future__ import annotations

import re

_SENTENCE_END = re.compile(r"[.!?](?=\s|$)")
# Em dash, en dash, horizontal bar, and the ASCII "--" stand-in. Escaped so no raw dash glyphs live in source.
_DASH = "\u2014|\u2013|\u2015|--"


def _replace_dash(match: re.Match) -> str:
    # A capital letter after the dash means a new thought: end the sentence. Otherwise use a comma.
    nxt = match.group(1)
    return ". " + nxt if nxt.isupper() else ", " + nxt


def remove_dashes(text: str) -> str:
    """Replace em dashes (and dash-like stand-ins) with commas or periods."""
    text = re.sub(r"(\d)\s*\u2013\s*(\d)", r"\1-\2", text)  # keep numeric ranges: 2020-2024
    text = re.sub(r"^[ \t]*(?:" + _DASH + r")+[ \t]*", "", text, flags=re.MULTILINE)  # sign-off dashes
    text = re.sub(r"[ \t]*(?:" + _DASH + r")+[ \t]*(\S)", _replace_dash, text)
    text = re.sub(r"[ \t]*(?:" + _DASH + r")+[ \t]*$", ".", text, flags=re.MULTILINE)
    text = re.sub(r"([.!?,]), ", r"\1 ", text)  # ".," or ",," artifacts
    text = re.sub(r",\.", ".", text)
    text = re.sub(r"([.!?])\. ", r"\1 ", text)
    return text


def strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), text)
    text = re.sub(r"^[ \t]{0,3}#{1,6}[ \t]*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[ \t]*[-*][ \t]+", "", text, flags=re.MULTILINE)
    return text


def limit_words(text: str, max_words: int) -> str:
    """Trim to max_words, preferring to cut at the last complete sentence."""
    words = text.split()
    if max_words <= 0 or len(words) <= max_words:
        return text
    # Walk the original text so paragraph breaks survive the cut.
    cut = 0
    for i, match in enumerate(re.finditer(r"\S+", text)):
        if i == max_words:
            break
        cut = match.end()
    clipped = text[:cut]
    ends = list(_SENTENCE_END.finditer(clipped))
    if ends and ends[-1].end() > len(clipped) // 2:
        return clipped[: ends[-1].end()].rstrip()
    return clipped.rstrip(" ,;:") + "."


def clean(text: str, max_words: int | None = None) -> str:
    text = text.replace("\r\n", "\n").strip()
    text = strip_markdown(remove_dashes(text))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    if max_words:
        text = limit_words(text, max_words)
    return text.strip()
