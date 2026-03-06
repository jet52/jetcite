"""Tests for North Dakota-specific citation patterns."""

from jetcite.patterns.states.nd import NDMatcher


def test_ndcc_section():
    m = NDMatcher()
    results = m.find_all("N.D.C.C. § 12.1-32-01")
    assert len(results) == 1
    assert results[0].normalized == "N.D.C.C. § 12.1-32-01"
    assert "ndlegis.gov" in results[0].sources[0].url
    assert "nameddest=12p1-32-01" in results[0].sources[0].url


def test_ndcc_no_periods():
    m = NDMatcher()
    results = m.find_all("NDCC § 1-02-13 ")
    assert len(results) == 1
    assert results[0].normalized == "N.D.C.C. § 1-02-13"


def test_ndcc_section_word():
    m = NDMatcher()
    results = m.find_all("section 14-02-05, N.D.C.C.")
    assert len(results) >= 1


def test_ndcc_chapter():
    m = NDMatcher()
    results = m.find_all("NDCC ch. 14-02")
    assert len(results) == 1
    assert results[0].normalized == "N.D.C.C. ch. 14-02"


def test_ndcc_decimal_title():
    m = NDMatcher()
    results = m.find_all("N.D.C.C. § 12.1-32-01 ")
    assert len(results) == 1
    c = results[0]
    assert c.components["title"] == "12"
    assert c.components["title_dec"] == "1"


def test_ndac_section():
    m = NDMatcher()
    results = m.find_all("N.D.A.C. § 43-02-05-01")
    assert len(results) == 1
    assert results[0].normalized == "N.D.A.C. § 43-02-05-01"
    assert "ndlegis.gov" in results[0].sources[0].url


def test_ndac_chapter():
    m = NDMatcher()
    results = m.find_all("N.D.A.C. ch. 43-02-05")
    assert len(results) == 1
    assert results[0].normalized == "N.D.A.C. ch. 43-02-05"


def test_nd_const():
    m = NDMatcher()
    results = m.find_all("N.D. Const. art. I, § 20")
    assert len(results) == 1
    assert results[0].normalized == "N.D. Const. art. I, § 20"
    assert "ndconst.org" in results[0].sources[0].url


def test_nd_const_long():
    m = NDMatcher()
    results = m.find_all("Article VI, section 2 of the North Dakota Constitution")
    assert len(results) == 1
    assert results[0].normalized == "N.D. Const. art. VI, § 2"


def test_nd_rule_civ_p():
    m = NDMatcher()
    results = m.find_all("N.D.R.Civ.P. Rule 56")
    assert len(results) >= 1
    found = [r for r in results if "ndrcivp" in r.components.get("rule_set", "")]
    assert len(found) >= 1
    assert "ndcourts.gov" in found[0].sources[0].url


def test_nd_rule_ev():
    m = NDMatcher()
    results = m.find_all("N.D.R.Ev. 803")
    assert len(results) == 1
    assert "ndrev" in results[0].components["rule_set"]


def test_nd_rule_crim_p():
    m = NDMatcher()
    results = m.find_all("N.D.R.Crim.P. 29")
    assert len(results) >= 1


def test_nd_rule_ct_3part():
    m = NDMatcher()
    results = m.find_all("N.D.R.Ct. 8.3.1")
    assert len(results) == 1
    assert "ndrct" in results[0].components["rule_set"]


def test_nd_admin_rule():
    m = NDMatcher()
    results = m.find_all("N.D. Sup. Ct. Admin. R. 1.2")
    assert len(results) == 1
    assert "ndsupctadminr" in results[0].components["rule_set"]


def test_nd_prof_conduct():
    m = NDMatcher()
    results = m.find_all("N.D.R. Prof. Conduct 1.1")
    assert len(results) == 1
    assert "ndrprofconduct" in results[0].components["rule_set"]


def test_local_rule():
    m = NDMatcher()
    results = m.find_all("Local Rule 100-1")
    assert len(results) == 1
    assert "local" in results[0].components["rule_set"]
