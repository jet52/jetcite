"""Tests for U.S. Constitution citation patterns."""

from jetcite.patterns.constitutions import USConstitutionMatcher


def test_us_const_article_section():
    m = USConstitutionMatcher()
    results = m.find_all("U.S. Const. art. III, § 2")
    assert len(results) == 1
    assert results[0].normalized == "U.S. Const. art. III, § 2"
    # Official source (Constitution Annotated) leads; Constitution Center
    # remains as the fetchable/unofficial fallback.
    assert results[0].sources[0].url == (
        "https://constitution.congress.gov/constitution/article-3/"
        "#article-3-section-2")
    # Avalon (frameable reading copy) second, Constitution Center third.
    assert results[0].sources[1].url == (
        "https://avalon.law.yale.edu/18th_century/art3.asp#3sec2")
    assert "constitutioncenter.org" in results[0].sources[2].url


def test_us_const_amendment():
    m = USConstitutionMatcher()
    results = m.find_all("U.S. Const. amend. XIV")
    assert len(results) == 1
    assert results[0].normalized == "U.S. Const. amend. XIV"
    assert results[0].sources[0].url == (
        "https://constitution.congress.gov/constitution/amendment-14/")
    assert results[0].sources[1].url == (
        "https://avalon.law.yale.edu/18th_century/amend1.asp#14")
    assert "amendment-xiv" in results[0].sources[2].url


def test_avalon_bill_of_rights_page_split():
    from jetcite.sources.avalon import avalon_amendment_url
    assert avalon_amendment_url("X").endswith("/rights1.asp#10")
    assert avalon_amendment_url("XI").endswith("/amend1.asp#11")


def test_legacy_dict_carries_avalon_url(tmp_path):
    from jetcite.legacy import to_legacy_dict
    m = USConstitutionMatcher()
    cite = m.find_all("U.S. Const. art. I, § 8")[0]
    entry = to_legacy_dict(cite, tmp_path)
    assert entry["avalon_url"] == (
        "https://avalon.law.yale.edu/18th_century/art1.asp#1sec8")
    assert "constitution.congress.gov" in entry["url"]


def test_us_const_amendment_section_anchor():
    m = USConstitutionMatcher()
    results = m.find_all("U.S. Const. amend. XIV, § 1")
    assert results[0].normalized == "U.S. Const. amend. XIV, § 1"
    assert results[0].sources[0].url == (
        "https://constitution.congress.gov/constitution/amendment-14/"
        "#amendment-14-section-1")


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
