"""Batch document scanning for citations."""

from __future__ import annotations

from jetcite.models import Citation
from jetcite.patterns import get_matchers


def scan_text(text: str) -> list[Citation]:
    """Scan text for all citations, deduplicated by normalized form.

    Returns citations in order of first appearance.
    """
    all_citations: list[Citation] = []
    seen: set[str] = set()

    matchers = get_matchers()
    for matcher in matchers:
        for cite in matcher.find_all(text):
            if cite.normalized not in seen:
                seen.add(cite.normalized)
                all_citations.append(cite)

    # Sort by position in source text
    all_citations.sort(key=lambda c: c.position)
    return all_citations


def lookup(text: str) -> Citation | None:
    """Look up a single citation string. Returns the first match."""
    matchers = get_matchers()
    for matcher in matchers:
        result = matcher.find_first(text)
        if result:
            return result
    return None
