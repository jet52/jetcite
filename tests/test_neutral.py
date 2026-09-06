"""Tests for medium-neutral citation patterns."""

from jetcite.patterns.neutral import NeutralCitationMatcher


def test_nd_neutral():
    m = NeutralCitationMatcher()
    results = m.find_all("2024 ND 156")
    assert len(results) == 1
    assert results[0].normalized == "2024 ND 156"
    assert results[0].jurisdiction == "nd"
    assert "ndcourts.gov" in results[0].sources[0].url


def test_nd_neutral_with_pinpoint():
    m = NeutralCitationMatcher()
    results = m.find_all("2024 ND 156, ¶ 12")
    assert len(results) == 1
    assert results[0].pinpoint == "¶ 12"


def test_nd_neutral_with_at_para_pinpoint():
    """Bluebook short form 'at ¶' parses as a full cite with pinpoint."""
    m = NeutralCitationMatcher()
    results = m.find_all("2024 ND 156 at ¶ 12")
    assert len(results) == 1
    assert results[0].normalized == "2024 ND 156"
    assert results[0].pinpoint == "¶ 12"


def test_ohio_neutral():
    m = NeutralCitationMatcher()
    results = m.find_all("2018-Ohio-3237")
    assert len(results) == 1
    assert results[0].normalized == "2018-Ohio-3237"


def test_nm_neutral():
    m = NeutralCitationMatcher()
    results = m.find_all("2009-NMSC-006")
    assert len(results) == 1
    assert results[0].jurisdiction == "nm"


def test_il_neutral():
    m = NeutralCitationMatcher()
    results = m.find_all("2011 IL 102345")
    assert len(results) == 1


def test_standard_neutral_co():
    m = NeutralCitationMatcher()
    results = m.find_all("2019 CO 44")
    assert len(results) == 1
    assert results[0].jurisdiction == "co"


def test_standard_neutral_sd():
    m = NeutralCitationMatcher()
    results = m.find_all("2013 S.D. 54")
    assert len(results) == 1
    assert results[0].jurisdiction == "sd"


def test_standard_neutral_mt():
    m = NeutralCitationMatcher()
    results = m.find_all("1998 MT 12")
    assert len(results) == 1
    assert results[0].jurisdiction == "mt"

def test_nd_neutral_period_spelled():
    """Period-spelled ND neutrals normalize to compact ND / ND App."""
    from jetcite import lookup

    m = NeutralCitationMatcher()
    for text, want in (
        ("2024 N.D. 156", "2024 ND 156"),
        ("1997 N.D. 24", "1997 ND 24"),
        ("2024 N. D. 156", "2024 ND 156"),
        ("2005 N.D. App. 8", "2005 ND App 8"),
        ("2005 N. D. App. 8", "2005 ND App 8"),
    ):
        results = m.find_all(text)
        assert len(results) == 1, text
        assert results[0].normalized == want, text
        assert results[0].jurisdiction == "nd"
        cite = lookup(text)
        assert cite is not None, text
        assert cite.normalized == want, text


def test_nd_neutral_compact_app_unchanged():
    m = NeutralCitationMatcher()
    results = m.find_all("2005 ND App 8")
    assert len(results) == 1
    assert results[0].normalized == "2005 ND App 8"

