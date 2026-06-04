"""Regression tests for page-break citation splice (phantom neutral cites).

A neutral citation split across a PDF page break, with the page-number footer
between the reporter token and the opinion number, was matched as the footer:
"2024 ND\\n\\n9\\n\\n\\n214" -> phantom "2024 ND 9" instead of "2024 ND 214".

Fixed by preprocess_document_text (strips page furniture before scanning) plus
the newline-tolerant-but-blank-line-rejecting gap in the neutral patterns. See
TODO.md, "Plan: Page-break citation splice."
"""

from pathlib import Path

from jetcite.patterns.neutral import NeutralCitationMatcher
from jetcite.scanner import scan_text

# Exact splice: "2024 ND" ends a page, "9" is the page-9 footer, "214, ¶ 16"
# begins the next page. Synthetic text modeled on a real page-break splice.
SPLICE = (
    "received proper notice. Doe v. Doe, 2024 ND\n"
    "\n"
    "9\n"
    "\n"
    "\n"
    "214, ¶ 16. In contrast, the appellant here was never served"
)

FIXTURE = Path(__file__).parent / "fixtures" / "page_break_citation.txt"


def test_no_phantom_from_page_number():
    """The page-number footer must not be captured as the opinion number."""
    m = NeutralCitationMatcher()
    normalized = {c.normalized for c in m.find_all(SPLICE)}
    assert "2024 ND 9" not in normalized


def test_recovers_real_citation():
    """After furniture stripping, the real cite is recovered intact."""
    m = NeutralCitationMatcher()
    by_norm = {c.normalized: c for c in m.find_all(SPLICE)}
    assert "2024 ND 214" in by_norm
    assert by_norm["2024 ND 214"].pinpoint == "¶ 16"


def test_scan_text_end_to_end():
    """The full scanner pipeline yields the real cite and no phantom."""
    normalized = {c.normalized for c in scan_text(SPLICE, resolve=False)}
    assert "2024 ND 214" in normalized
    assert "2024 ND 9" not in normalized


def test_sibling_pattern_montana():
    """Gap-tightening must not be ND-only: a split MT cite behaves the same."""
    m = NeutralCitationMatcher()
    text = "See Smith v. Jones, 2019 MT\n\n7\n\n\n245, ¶ 3 (holding...)."
    normalized = {c.normalized for c in m.find_all(text)}
    assert "2019 MT 7" not in normalized
    assert "2019 MT 245" in normalized


def test_fixture_present_and_reproduces_splice():
    """Guards the committed fixture so the repro can't silently disappear."""
    text = FIXTURE.read_text()
    assert "2024 ND" in text
    # The footer "9" sits alone on a line between the two halves of the cite.
    assert "\n9\n" in text
