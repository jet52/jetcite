"""Tests for federal case reporter citation patterns."""

from jetcite.patterns.federal_cases import FederalCaseMatcher


def test_us_reports():
    m = FederalCaseMatcher()
    results = m.find_all("505 U.S. 377")
    assert len(results) == 1
    assert results[0].normalized == "505 U.S. 377"
    assert "justia.com" in results[0].sources[0].url


def test_federal_reporter_3d():
    m = FederalCaseMatcher()
    results = m.find_all("400 F.3d 500")
    assert len(results) == 1
    assert results[0].normalized == "400 F.3d 500"


def test_federal_reporter_4th():
    m = FederalCaseMatcher()
    results = m.find_all("50 F.4th 100")
    assert len(results) == 1
    assert results[0].normalized == "50 F.4th 100"


def test_s_ct():
    m = FederalCaseMatcher()
    results = m.find_all("140 S. Ct. 1731")
    assert len(results) == 1
    assert results[0].normalized == "140 S. Ct. 1731"


def test_f_supp_3d():
    m = FederalCaseMatcher()
    results = m.find_all("500 F. Supp. 3d 100")
    assert len(results) == 1
    assert results[0].normalized == "500 F. Supp. 3d 100"


def test_l_ed_2d():
    m = FederalCaseMatcher()
    results = m.find_all("120 L. Ed. 2d 500")
    assert len(results) == 1
    assert results[0].normalized == "120 L. Ed. 2d 500"


def test_br():
    m = FederalCaseMatcher()
    results = m.find_all("300 B.R. 50")
    assert len(results) == 1
    assert results[0].normalized == "300 B.R. 50"
