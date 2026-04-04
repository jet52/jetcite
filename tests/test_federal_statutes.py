"""Tests for federal statute citation patterns."""

from jetcite.patterns.federal_statutes import FederalStatuteMatcher


def test_usc():
    m = FederalStatuteMatcher()
    results = m.find_all("42 U.S.C. § 1983")
    assert len(results) == 1
    assert results[0].normalized == "42 U.S.C. § 1983"
    assert "govinfo.gov" in results[0].sources[0].url


def test_usc_no_periods():
    m = FederalStatuteMatcher()
    results = m.find_all("42 USC § 1983")
    assert len(results) == 1
    assert results[0].normalized == "42 U.S.C. § 1983"


def test_usc_with_subsection():
    m = FederalStatuteMatcher()
    results = m.find_all("42 U.S.C. § 1983(1)")
    assert len(results) == 1
    assert "(1)" in results[0].normalized


def test_cfr():
    m = FederalStatuteMatcher()
    results = m.find_all("29 C.F.R. § 1910.1200")
    assert len(results) == 1
    assert results[0].normalized == "29 C.F.R. § 1910.1200"
    assert "ecfr.gov" in results[0].sources[0].url


def test_cfr_no_periods():
    m = FederalStatuteMatcher()
    results = m.find_all("29 CFR 1910.1200")
    assert len(results) == 1


# ── Real citations from ND opinions ──────────────────────────────


def test_real_usc_28():
    """28 U.S.C. § 1738 — Full Faith and Credit, from 2020 ND 243."""
    m = FederalStatuteMatcher()
    results = m.find_all("28 U.S.C. § 1738")
    assert len(results) == 1
    assert results[0].components["title"] == "28"
    assert results[0].components["section"] == "1738"


def test_real_usc_42():
    """42 U.S.C. § 1983 — from 2020 ND 98."""
    m = FederalStatuteMatcher()
    results = m.find_all("42 U.S.C. § 1983")
    assert len(results) == 1
    assert "govinfo.gov" in results[0].sources[0].url


def test_real_cfr_nested_subsection():
    """40 C.F.R. § 52.21 — from ND clean air opinions."""
    m = FederalStatuteMatcher()
    results = m.find_all("40 C.F.R. § 52.21")
    assert len(results) == 1
    assert results[0].components["title"] == "40"
    assert results[0].components["section"] == "52.21"
