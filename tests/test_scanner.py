"""Tests for the batch scanner."""

from jetcite.scanner import lookup, scan_text


def test_scan_deduplication():
    text = "See 2024 ND 156, ¶ 12. The court in 2024 ND 156 also held..."
    results = scan_text(text)
    nd_cites = [r for r in results if r.normalized == "2024 ND 156"]
    assert len(nd_cites) == 1


def test_scan_multiple_types():
    text = (
        "Under 42 U.S.C. § 1983, the plaintiff sued. "
        "The court cited 2024 ND 156. "
        "See also N.D.C.C. § 1-02-13. "
    )
    results = scan_text(text)
    types = {r.cite_type.value for r in results}
    assert "statute" in types
    assert "case" in types


def test_scan_ordering():
    text = "First 2024 ND 156, then 42 U.S.C. § 1983."
    results = scan_text(text)
    # Results should be in document order
    assert results[0].position < results[1].position


def test_lookup_single():
    result = lookup("585 N.W.2d 123")
    assert result is not None
    assert result.cite_type.value == "case"


def test_lookup_no_match():
    result = lookup("not a citation")
    assert result is None
