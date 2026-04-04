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


# ── Real citations from ND opinions ──────────────────────────────


def test_real_f2d():
    """392 F.2d 60 — from 2020 ND 114."""
    m = FederalCaseMatcher()
    results = m.find_all("392 F.2d 60")
    assert len(results) == 1
    assert results[0].components["volume"] == "392"
    assert results[0].components["reporter"] == "F.2d"
    assert results[0].components["page"] == "60"


def test_real_f3d():
    """152 F.3d 680 — from 2020 ND 124."""
    m = FederalCaseMatcher()
    results = m.find_all("152 F.3d 680")
    assert len(results) == 1
    assert results[0].normalized == "152 F.3d 680"


def test_real_fsupp2d():
    """903 F. Supp. 2d 333 — from 2024 ND 162."""
    m = FederalCaseMatcher()
    results = m.find_all("903 F. Supp. 2d 333")
    assert len(results) == 1
    assert results[0].components["reporter"] == "F. Supp. 2d"


def test_real_frd():
    """174 F.R.D. 643 — from ND opinions."""
    m = FederalCaseMatcher()
    results = m.find_all("174 F.R.D. 643")
    assert len(results) == 1
    assert results[0].components["reporter"] == "F.R.D."


def test_real_us_reports():
    """466 U.S. 668 — Strickland v. Washington, from 2020 ND 128."""
    m = FederalCaseMatcher()
    results = m.find_all("466 U.S. 668")
    assert len(results) == 1
    assert "justia.com" in results[0].sources[0].url


def test_real_s_ct():
    """141 S. Ct. 2063 — Cedar Point Nursery, from 2024 ND 109."""
    m = FederalCaseMatcher()
    results = m.find_all("141 S. Ct. 2063")
    assert len(results) == 1
    assert results[0].components["reporter"] == "S. Ct."


def test_real_l_ed_2d():
    """128 L. Ed. 2d 767 — from 2024 ND opinions."""
    m = FederalCaseMatcher()
    results = m.find_all("128 L. Ed. 2d 767")
    assert len(results) == 1
    assert results[0].components["reporter"] == "L. Ed. 2d"
