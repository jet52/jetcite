"""Tests for Arizona-specific citation patterns."""

from jetcite.models import CitationType
from jetcite.patterns.neutral import NeutralCitationMatcher
from jetcite.patterns.states.az import AZMatcher


def test_ars_section():
    m = AZMatcher()
    results = m.find_all("A.R.S. § 13-1105")
    assert len(results) == 1
    c = results[0]
    assert c.cite_type == CitationType.STATUTE
    assert c.jurisdiction == "az"
    assert c.normalized == "A.R.S. § 13-1105"
    assert c.sources[0].url == "https://www.azleg.gov/ars/13/01105.htm"


def test_ars_no_periods():
    m = AZMatcher()
    results = m.find_all("see ARS 13-105 generally")
    assert len(results) == 1
    assert results[0].normalized == "A.R.S. § 13-105"
    assert results[0].sources[0].url == "https://www.azleg.gov/ars/13/00105.htm"


def test_ars_decimal_section():
    m = AZMatcher()
    results = m.find_all("A.R.S. § 12-821.01")
    assert len(results) == 1
    assert results[0].normalized == "A.R.S. § 12-821.01"
    assert results[0].sources[0].url == "https://www.azleg.gov/ars/12/00821-01.htm"


def test_ars_long_form_with_subsection():
    m = AZMatcher()
    results = m.find_all("Ariz. Rev. Stat. Ann. § 13-1105(A)")
    assert len(results) == 1
    assert results[0].normalized == "A.R.S. § 13-1105"


def test_ars_ignores_word_cars():
    m = AZMatcher()
    assert m.find_all("The cars 12-345 were parked.") == []


def test_aac_section():
    m = AZMatcher()
    results = m.find_all("A.A.C. R20-6-201")
    assert len(results) == 1
    c = results[0]
    assert c.cite_type == CitationType.REGULATION
    assert c.normalized == "Ariz. Admin. Code R20-6-201"
    assert c.sources[0].url == (
        "https://apps.azsos.gov/public_services/Title_20/20-06.pdf"
    )


def test_aac_long_form_pads_title():
    m = AZMatcher()
    results = m.find_all("Ariz. Admin. Code R2-6-101")
    assert len(results) == 1
    assert results[0].sources[0].url == (
        "https://apps.azsos.gov/public_services/Title_02/2-06.pdf"
    )


def test_constitution_arabic():
    m = AZMatcher()
    results = m.find_all("Ariz. Const. art. 2, § 4")
    assert len(results) == 1
    c = results[0]
    assert c.cite_type == CitationType.CONSTITUTION
    assert c.normalized == "Ariz. Const. art. 2, § 4"
    assert c.sources[0].url == "https://www.azleg.gov/const/2/4.htm"


def test_constitution_roman_normalizes_to_arabic():
    m = AZMatcher()
    results = m.find_all("Ariz. Const. art. II, § 4")
    assert len(results) == 1
    assert results[0].normalized == "Ariz. Const. art. 2, § 4"
    assert results[0].sources[0].url == "https://www.azleg.gov/const/2/4.htm"


def test_constitution_article_4_part():
    m = AZMatcher()
    results = m.find_all("Ariz. Const. art. 4, pt. 2, § 2")
    assert len(results) == 1
    assert results[0].normalized == "Ariz. Const. art. 4, pt. 2, § 2"
    assert results[0].sources[0].url == "https://www.azleg.gov/const/4/2.p2.htm"


def test_court_rule_civil():
    m = AZMatcher()
    results = m.find_all("Ariz. R. Civ. P. 12(b)(6)")
    assert len(results) == 1
    c = results[0]
    assert c.cite_type == CitationType.COURT_RULE
    assert c.jurisdiction == "az"
    assert c.normalized == "Ariz. R. Civ. P. 12"
    assert c.sources[0].url == "https://www.azcourts.gov/rules"


def test_court_rule_evidence():
    m = AZMatcher()
    results = m.find_all("Ariz. R. Evid. 401")
    assert len(results) == 1
    assert results[0].normalized == "Ariz. R. Evid. 401"


def test_court_rule_civil_appellate():
    m = AZMatcher()
    results = m.find_all("Ariz. R. Civ. App. P. 9")
    assert len(results) == 1
    assert results[0].normalized == "Ariz. R. Civ. App. P. 9"


def test_rev_stat_no_symbol_is_statute_not_rule():
    # "Ariz. Rev. Stat. Ann. 13-1105" must parse as a statute, never a court rule.
    m = AZMatcher()
    results = m.find_all("Ariz. Rev. Stat. Ann. 13-1105")
    assert len(results) == 1
    assert results[0].cite_type == CitationType.STATUTE
    assert results[0].normalized == "A.R.S. § 13-1105"


def test_no_spurious_az_neutral():
    # Arizona has no medium-neutral citation; "2024 AZ 12" must not resolve.
    results = NeutralCitationMatcher().find_all("2024 AZ 12")
    assert [r for r in results if r.jurisdiction == "az"] == []
