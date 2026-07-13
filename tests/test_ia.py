"""Tests for Iowa-specific citation patterns."""

from jetcite.models import CitationType
from jetcite.patterns.states.ia import IAMatcher


def test_iowa_code_section():
    m = IAMatcher()
    results = m.find_all("Iowa Code § 707.2")
    assert len(results) == 1
    c = results[0]
    assert c.cite_type == CitationType.STATUTE
    assert c.jurisdiction == "ia"
    assert c.normalized == "Iowa Code § 707.2"
    assert c.sources[0].url == "https://www.legis.iowa.gov/docs/code/707.2.pdf"


def test_iowa_code_no_section_symbol():
    m = IAMatcher()
    results = m.find_all("under Iowa Code 321.285 the driver")
    assert len(results) == 1
    assert results[0].normalized == "Iowa Code § 321.285"


def test_iowa_code_chapter():
    m = IAMatcher()
    results = m.find_all("Iowa Code ch. 707")
    assert len(results) == 1
    assert results[0].normalized == "Iowa Code ch. 707"
    assert results[0].sources[0].url == "https://www.legis.iowa.gov/docs/code/707.pdf"


def test_iowa_code_subsection_ignored():
    m = IAMatcher()
    results = m.find_all("Iowa Code § 4.1(30)")
    assert len(results) == 1
    assert results[0].normalized == "Iowa Code § 4.1"


def test_iowa_admin_rule():
    m = IAMatcher()
    results = m.find_all("Iowa Admin. Code r. 657-8.1")
    assert len(results) == 1
    c = results[0]
    assert c.cite_type == CitationType.REGULATION
    assert c.normalized == "Iowa Admin. Code r. 657-8.1"
    assert c.sources[0].url == (
        "https://www.legis.iowa.gov/docs/aco/rule/657.8.1.pdf"
    )


def test_iowa_court_rule_civil():
    m = IAMatcher()
    results = m.find_all("Iowa R. Civ. P. 1.302")
    assert len(results) == 1
    c = results[0]
    assert c.cite_type == CitationType.COURT_RULE
    assert c.normalized == "Iowa R. Civ. P. 1.302"
    assert c.sources[0].url == (
        "https://www.legis.iowa.gov/docs/ACO/CourtRulesChapter/1.pdf"
    )


def test_iowa_court_rule_appellate():
    m = IAMatcher()
    results = m.find_all("Iowa R. App. P. 6.904")
    assert len(results) == 1
    assert results[0].normalized == "Iowa R. App. P. 6.904"
    assert results[0].sources[0].url == (
        "https://www.legis.iowa.gov/docs/ACO/CourtRulesChapter/6.pdf"
    )


def test_iowa_constitution():
    m = IAMatcher()
    results = m.find_all("Iowa Const. art. I, § 8")
    assert len(results) == 1
    c = results[0]
    assert c.cite_type == CitationType.CONSTITUTION
    assert c.normalized == "Iowa Const. art. I, § 8"
    assert c.sources[0].url == (
        "https://www.legis.iowa.gov/docs/publications/icnst/402726.pdf"
    )
