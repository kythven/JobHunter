"""Cleanup helper for raw job descriptions pulled from Adzuna/Reed."""
import re

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def clean_description(text: str) -> str:
    """Strip HTML tags and collapse whitespace. No filtering/summarizing —
    just makes the raw description readable in the digest."""
    if not text:
        return ""
    text = _TAG.sub(" ", text)
    text = _WS.sub(" ", text).strip()
    return text
