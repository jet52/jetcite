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


# ── Truncation regression: pin-cite short forms (Gion redline 2026-04-25) ────


def test_pin_cite_no_truncation_f3d():
    """`491 F.3d at 363` must NOT produce a phantom `491 F. 3` citation.

    Before the fix, the regex backtracked through the optional series group
    and emitted a malformed citation with page='3'.
    """
    m = FederalCaseMatcher()
    results = m.find_all("See Goss, 491 F.3d at 363.")
    assert results == []


def test_pin_cite_no_truncation_f2d():
    """`731 F.2d at 915` must produce no citation, not `731 F. 2`."""
    m = FederalCaseMatcher()
    results = m.find_all("Laker, 731 F.2d at 915.")
    assert results == []


def test_full_cite_then_pin_cite_dedup():
    """Document with full cite plus pin-cite back-reference yields one entry."""
    m = FederalCaseMatcher()
    text = (
        "Goss, 491 F.3d 355, 363 (8th Cir. 2007); "
        "see also Goss, 491 F.3d at 365."
    )
    results = m.find_all(text)
    # Expect exactly one match: the full cite. The pin cite is rejected.
    assert len(results) == 1
    assert results[0].normalized == "491 F.3d 355"


def test_federal_first_series():
    """Pre-1924 Federal Reporter (no series marker): `200 F. 100`."""
    m = FederalCaseMatcher()
    results = m.find_all("200 F. 100")
    assert len(results) == 1
    assert results[0].normalized == "200 F. 100"
    assert results[0].components["reporter"] == "F."


def test_federal_first_series_does_not_match_modern():
    """First-series pattern must not match `491 F.3d 355` (modern series)."""
    m = FederalCaseMatcher()
    results = m.find_all("491 F.3d 355")
    # Exactly one match — from the modern-series pattern, not the first-series one.
    assert len(results) == 1
    assert results[0].components["reporter"] == "F.3d"


def test_f_supp_first_series():
    """Pre-1988 F. Supp. (no series marker): `100 F. Supp. 200`."""
    m = FederalCaseMatcher()
    results = m.find_all("100 F. Supp. 200")
    assert len(results) == 1
    assert results[0].normalized == "100 F. Supp. 200"
    assert results[0].components["reporter"] == "F. Supp."


def test_f_supp_first_does_not_match_modern():
    """First-series F. Supp. pattern must not match `195 F. Supp. 3d 776`."""
    m = FederalCaseMatcher()
    results = m.find_all("195 F. Supp. 3d 776")
    assert len(results) == 1
    assert results[0].components["reporter"] == "F. Supp. 3d"
