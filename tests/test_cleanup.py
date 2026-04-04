"""Tests for the markdown cleanup module.

Tests use real-world patterns from ND Supreme Court opinions and
NDCC/NDAC statutes.
"""

import pytest

from jetcite.cleanup import (
    cleanup,
    cleanup_html,
    cleanup_opinion,
    cleanup_regulation,
    cleanup_statute,
    _collapse_consecutive_blanks,
    _collapse_intra_paragraph_blanks,
    _ensure_inter_paragraph_blanks,
    _identify_page_number_lines,
    _reattach_detached_markers,
    _remove_page_numbers,
    _split_concatenated_stamps,
    _strip_trailing_page_number,
)
from jetcite.models import CitationType


# ── Page number removal ───────────────────────────────────────────


def test_page_numbers_sequential():
    lines = ["text", "", "1", "", "more text", "", "2", "", "end"]
    nums = _identify_page_number_lines(lines)
    assert 2 in nums
    assert 6 in nums


def test_page_numbers_not_sequential():
    lines = ["text", "", "99", "", "more text", "", "3", "", "end"]
    nums = _identify_page_number_lines(lines)
    assert len(nums) == 0


def test_remove_page_numbers():
    lines = ["para one", "", "1", "", "para two"]
    result = _remove_page_numbers(lines)
    assert "1" not in [l.strip() for l in result]
    assert "para one" in result
    assert "para two" in result


# ── Blank line collapsing ─────────────────────────────────────────


def test_collapse_consecutive_blanks():
    lines = ["a", "", "", "", "b", "", "c"]
    result = _collapse_consecutive_blanks(lines)
    assert result == ["a", "", "b", "", "c"]


# ── Paragraph marker reattachment ─────────────────────────────────


def test_reattach_detached_marker():
    lines = ["[¶5]", "", "The court held that the statute was valid."]
    result = _reattach_detached_markers(lines)
    assert len(result) == 1
    assert result[0].startswith("[¶5]")
    assert "statute was valid" in result[0]


def test_reattach_with_preceding_text():
    lines = ["argued that", "[¶6]", "", "The district court erred."]
    result = _reattach_detached_markers(lines)
    assert any("[¶6]" in line and "argued that" in line for line in result)


# ── Inter-paragraph blanks ────────────────────────────────────────


def test_ensure_inter_paragraph_blanks():
    lines = ["[¶1] First paragraph.", "[¶2] Second paragraph."]
    result = _ensure_inter_paragraph_blanks(lines)
    # Should have blank line before ¶2 but not before ¶1
    assert result[0] == "[¶1] First paragraph."
    assert result[1] == ""
    assert result[2] == "[¶2] Second paragraph."


# ── Intra-paragraph blank collapsing ──────────────────────────────


def test_collapse_intra_paragraph_blanks():
    lines = [
        "[¶3] The district court found that the defendant",
        "",
        "had violated the statute when he failed to comply",
        "",
        "with the terms of the agreement.",
        "",
        "[¶4] We affirm.",
    ]
    result = _collapse_intra_paragraph_blanks(lines)
    # ¶3 should be joined into one line
    para3 = [l for l in result if "[¶3]" in l]
    assert len(para3) == 1
    assert "defendant had violated" in para3[0]
    assert "terms of the agreement" in para3[0]


# ── Filing stamp splitting ────────────────────────────────────────


def test_split_concatenated_stamps():
    lines = ["Clerk of Supreme CourtThis opinion was filed."]
    result = _split_concatenated_stamps(lines)
    assert len(result) == 2
    assert result[0] == "Clerk of Supreme Court"
    assert result[1] == "This opinion was filed."


# ── Trailing page number ─────────────────────────────────────────


def test_strip_trailing_page_number():
    lines = ["last paragraph", "", "15", "", ""]
    result = _strip_trailing_page_number(lines)
    assert result[-1] == ""  # trailing newline
    assert "15" not in [l.strip() for l in result]


# ── Full opinion cleanup ─────────────────────────────────────────


def test_cleanup_opinion_short_text():
    """Short text should be returned as-is."""
    assert cleanup_opinion("short") == "short"


def test_cleanup_opinion_full_pipeline():
    text = "\n".join([
        "# State v. Smith, 2024 ND 42",
        "",
        "[¶1] This is paragraph one",
        "that spans multiple lines.",
        "",
        "1",
        "",
        "[¶2] This is paragraph two",
        "",
        "that was split by a page break.",
        "",
        "[¶3] Final paragraph.",
        "",
        "2",
        "",
        "",
    ])
    result = cleanup_opinion(text)
    lines = result.split("\n")
    # Page numbers should be removed
    assert "1" not in [l.strip() for l in lines if l.strip().isdigit()]
    # Paragraphs should be present
    assert any("[¶1]" in l for l in lines)
    assert any("[¶2]" in l for l in lines)


# ── Statute cleanup ──────────────────────────────────────────────


def test_cleanup_statute_section_headings():
    text = "\n".join([
        "TITLE 1",
        "GENERAL PROVISIONS",
        "Page No. 1",
        "1-01-01. General principles. This chapter governs interpretation.",
        "1-01-02. Effective date. This code takes effect July 1.",
    ])
    result = cleanup_statute(text)
    assert "### § 1-01-01. General principles." in result
    assert "### § 1-01-02. Effective date." in result
    assert "TITLE 1" not in result
    assert "Page No." not in result


def test_cleanup_statute_toc_filtering():
    """TOC entries (no trailing period) should be filtered."""
    text = "\n".join([
        "1-01-01 General principles",
        "1-01-02 Effective date",
        "1-01-01. General principles. This chapter governs interpretation.",
    ])
    result = cleanup_statute(text)
    # Only the real section should survive, not the TOC entries
    assert "### § 1-01-01." in result
    lines = [l for l in result.split("\n") if l.strip()]
    # Should not have the bare TOC entries
    assert not any(l.strip() == "1-01-01 General principles" for l in lines)


def test_cleanup_statute_allcaps_headers():
    text = "GENERAL PROVISIONS\n1-01-01. Definitions. The following definitions apply."
    result = cleanup_statute(text)
    assert "GENERAL PROVISIONS" not in result
    assert "### § 1-01-01." in result


# ── Regulation cleanup ───────────────────────────────────────────


def test_cleanup_regulation_section_headings():
    text = "43-02-05-01. Purpose. This chapter establishes requirements."
    result = cleanup_regulation(text)
    assert "### § 43-02-05-01. Purpose." in result


def test_cleanup_regulation_requires_four_parts():
    """NDAC sections require 4+ parts; 3-part numbers are not sections."""
    text = "43-02-05 General rules\n43-02-05-01. Purpose. This chapter applies."
    result = cleanup_regulation(text)
    # The 3-part entry is not a section heading
    assert "### § 43-02-05." not in result
    assert "### § 43-02-05-01." in result


# ── Generic HTML cleanup ─────────────────────────────────────────


def test_cleanup_html_blank_lines():
    text = "\n\n\nSome content\n\n\n\nMore content\n\n"
    result = cleanup_html(text)
    assert "\n\n\n" not in result
    assert result.startswith("Some content")
    assert result.endswith("\n")


def test_cleanup_html_trailing_whitespace():
    text = "line one   \nline two  \n"
    result = cleanup_html(text)
    assert "   " not in result


# ── Dispatcher ────────────────────────────────────────────────────


def test_dispatch_case():
    """Case citations route to opinion cleanup."""
    text = "x" * 100  # long enough to not short-circuit
    result = cleanup(text, CitationType.CASE)
    assert isinstance(result, str)


def test_dispatch_nd_statute():
    text = "1-01-01. Definitions. The following apply."
    result = cleanup(text, CitationType.STATUTE, jurisdiction="nd")
    assert "### §" in result


def test_dispatch_nd_regulation():
    text = "43-02-05-01. Purpose. This chapter establishes requirements."
    result = cleanup(text, CitationType.REGULATION, jurisdiction="nd")
    assert "### §" in result


def test_dispatch_us_statute():
    """US statutes get generic HTML cleanup."""
    text = "\n\nSome USC content\n\n\n"
    result = cleanup(text, CitationType.STATUTE, jurisdiction="us")
    assert result.startswith("Some USC content")


def test_dispatch_constitution():
    text = "\n\nConstitutional text\n\n"
    result = cleanup(text, CitationType.CONSTITUTION, jurisdiction="us")
    assert result.startswith("Constitutional text")
