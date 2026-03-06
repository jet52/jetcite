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
