"""Tests for U.S. Constitution citation patterns."""

from jetcite.patterns.constitutions import USConstitutionMatcher


def test_us_const_article_section():
    m = USConstitutionMatcher()
    results = m.find_all("U.S. Const. art. III, § 2")
    assert len(results) == 1
    assert results[0].normalized == "U.S. Const. art. III, § 2"
    assert "constitutioncenter.org" in results[0].sources[0].url


def test_us_const_amendment():
    m = USConstitutionMatcher()
    results = m.find_all("U.S. Const. amend. XIV")
    assert len(results) == 1
    assert results[0].normalized == "U.S. Const. amend. XIV"
    assert "amendment-xiv" in results[0].sources[0].url


def test_us_const_article_of():
    m = USConstitutionMatcher()
    results = m.find_all("Article III of the U.S. Constitution")
    assert len(results) == 1
    assert results[0].normalized == "U.S. Const. art. III"


def test_us_const_amendment_to():
    m = USConstitutionMatcher()
    results = m.find_all("Amendment XIV to the United States Constitution")
    assert len(results) == 1
    assert results[0].normalized == "U.S. Const. amend. XIV"


def test_us_const_flexible_spacing():
    m = USConstitutionMatcher()
    results = m.find_all("US Const. amend. V")
    assert len(results) == 1
    assert results[0].normalized == "U.S. Const. amend. V"


# ── Real citations from ND opinions ──────────────────────────────


def test_real_amend_iv():
    """U.S. Const. amend. IV — from 2024 ND 115."""
    m = USConstitutionMatcher()
    results = m.find_all("U.S. Const. amend. IV")
    assert len(results) == 1
    assert results[0].components["amendment"] == "IV"


def test_real_amend_vi():
    """U.S. Const. amend. VI — from 2020 ND 48."""
    m = USConstitutionMatcher()
    results = m.find_all("U.S. Const. amend. VI")
    assert len(results) == 1
    assert results[0].components["amendment"] == "VI"


def test_real_amend_with_section():
    """U.S. Const. amend. XIV, § 1 — due process clause."""
    m = USConstitutionMatcher()
    results = m.find_all("U.S. Const. amend. XIV, § 1")
    assert len(results) == 1
    assert results[0].components["amendment"] == "XIV"
    assert results[0].components["section"] == "1"
