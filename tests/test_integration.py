"""Integration tests using fixture documents to verify all citation types are found."""

import os

import pytest

from jetcite.scanner import scan_text


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return f.read()


def _scan_fixture(name: str) -> list:
    return scan_text(_load_fixture(name))


# ── all_citation_types.txt ──────────────────────────────────────────


@pytest.fixture(scope="module")
def all_cites():
    return _scan_fixture("all_citation_types.txt")


def _find(cites, normalized):
    return [c for c in cites if c.normalized == normalized]


def _find_containing(cites, substring):
    return [c for c in cites if substring in c.normalized]


# --- US Constitution ---

def test_us_const_amend(all_cites):
    matches = _find(all_cites, "U.S. Const. amend. I")
    assert len(matches) >= 1
    assert matches[0].cite_type.value == "constitution"


def test_us_const_art_sec(all_cites):
    matches = _find(all_cites, "U.S. Const. art. VI, § 2")
    assert len(matches) == 1


def test_us_const_amend_sec(all_cites):
    matches = _find(all_cites, "U.S. Const. amend. XIV, § 1")
    assert len(matches) == 1


# --- ND Constitution ---

def test_nd_const_short(all_cites):
    matches = _find(all_cites, "N.D. Const. art. I, § 20")
    assert len(matches) >= 1
    assert matches[0].cite_type.value == "constitution"


def test_nd_const_long(all_cites):
    matches = _find(all_cites, "N.D. Const. art. XI, § 6")
    assert len(matches) == 1


def test_nd_const_forgiving(all_cites):
    matches = _find(all_cites, "N.D. Const. art. I, § 12")
    assert len(matches) >= 1


# --- Federal Statutes ---

def test_usc_standard(all_cites):
    matches = _find(all_cites, "42 U.S.C. § 1983")
    assert len(matches) >= 1
    assert matches[0].cite_type.value == "statute"


def test_usc_subsection(all_cites):
    matches = _find(all_cites, "18 U.S.C. § 922(g)(1)")
    assert len(matches) == 1


def test_usc_forgiving(all_cites):
    matches = _find(all_cites, "42 U.S.C. § 1988")
    assert len(matches) >= 1


# --- CFR ---

def test_cfr_standard(all_cites):
    matches = _find(all_cites, "29 C.F.R. § 1910.1200")
    assert len(matches) >= 1
    assert matches[0].cite_type.value == "regulation"


def test_cfr_no_periods(all_cites):
    matches = _find_containing(all_cites, "40 C.F.R.")
    assert len(matches) >= 1


# --- Federal Rules ---

def test_frcp(all_cites):
    matches = _find(all_cites, "Fed. R. Civ. P. 56")
    assert len(matches) >= 1
    assert matches[0].cite_type.value == "court_rule"


def test_frcp_subsection(all_cites):
    matches = _find(all_cites, "Fed. R. Civ. P. 12(b)(6)")
    assert len(matches) >= 1


def test_fre(all_cites):
    matches = _find(all_cites, "Fed. R. Evid. 801")
    assert len(matches) >= 1


def test_frap(all_cites):
    matches = _find(all_cites, "Fed. R. App. P. 28")
    assert len(matches) >= 1


def test_frcrp(all_cites):
    matches = _find(all_cites, "Fed. R. Crim. P. 29")
    assert len(matches) >= 1


def test_frbp(all_cites):
    matches = _find(all_cites, "Fed. R. Bankr. P. 7001")
    assert len(matches) >= 1


# --- NDCC ---

def test_ndcc_standard(all_cites):
    matches = _find(all_cites, "N.D.C.C. § 1-02-13")
    assert len(matches) >= 1
    assert matches[0].cite_type.value == "statute"


def test_ndcc_decimal(all_cites):
    matches = _find(all_cites, "N.D.C.C. § 12.1-32-01")
    assert len(matches) >= 1


def test_ndcc_decimal_subsection(all_cites):
    matches = _find(all_cites, "N.D.C.C. § 12.1-32-01.1")
    assert len(matches) == 1


def test_ndcc_chapter(all_cites):
    matches = _find(all_cites, "N.D.C.C. ch. 14-02")
    assert len(matches) >= 1


# --- NDAC ---

def test_ndac_section(all_cites):
    matches = _find(all_cites, "N.D.A.C. § 43-02-05-01")
    assert len(matches) >= 1


def test_ndac_chapter(all_cites):
    matches = _find(all_cites, "N.D.A.C. ch. 43-02-05")
    assert len(matches) >= 1


# --- ND Court Rules ---

def test_nd_rcivp(all_cites):
    matches = _find(all_cites, "N.D.R.Civ.P. 56")
    assert len(matches) >= 1
    assert matches[0].cite_type.value == "court_rule"


def test_nd_rcrimp(all_cites):
    matches = _find(all_cites, "N.D.R.Crim.P. 29")
    assert len(matches) >= 1


def test_nd_rapp(all_cites):
    matches = _find(all_cites, "N.D.R.App.P. 28")
    assert len(matches) >= 1


def test_nd_rev(all_cites):
    matches = _find(all_cites, "N.D.R.Ev. 803")
    assert len(matches) >= 1


def test_nd_rct_three_part(all_cites):
    matches = _find(all_cites, "N.D.R.Ct. 8.3.1")
    assert len(matches) == 1


def test_nd_rct_two_part(all_cites):
    matches = _find(all_cites, "N.D.R.Ct. 11.10")
    assert len(matches) == 1


def test_nd_sup_ct_admin(all_cites):
    matches = _find_containing(all_cites, "N.D. Sup. Ct. Admin. R.")
    assert len(matches) >= 1


def test_nd_prof_conduct(all_cites):
    matches = _find(all_cites, "N.D.R. Prof. Conduct 1.1")
    assert len(matches) == 1


# --- Medium-neutral citations ---

def test_nd_neutral(all_cites):
    matches = _find(all_cites, "2024 ND 156")
    assert len(matches) >= 1
    assert matches[0].cite_type.value == "case"


def test_ohio_neutral(all_cites):
    matches = _find(all_cites, "2018-Ohio-3237")
    assert len(matches) == 1


def test_nm_sc_neutral(all_cites):
    matches = _find(all_cites, "2009-NMSC-006")
    assert len(matches) == 1


def test_il_neutral(all_cites):
    matches = _find(all_cites, "2011 IL 102345")
    assert len(matches) == 1


def test_co_neutral(all_cites):
    matches = _find(all_cites, "2019 CO 44")
    assert len(matches) == 1


# --- Regional Reporters ---
# Note: normalization keeps spaces in reporter names (e.g., "N.W. 2d")

def test_nw2d(all_cites):
    matches = _find(all_cites, "585 N.W. 2d 123")
    assert len(matches) >= 1
    assert matches[0].cite_type.value == "case"


def test_nw3d(all_cites):
    matches = _find(all_cites, "993 N.W. 3d 374")
    assert len(matches) >= 1


def test_nw_first(all_cites):
    matches = _find(all_cites, "100 N.W. 500")
    assert len(matches) >= 1


def test_a3d(all_cites):
    matches = _find(all_cites, "200 A. 3d 400")
    assert len(matches) == 1


def test_se2d(all_cites):
    matches = _find(all_cites, "300 S.E. 2d 100")
    assert len(matches) == 1


def test_so3d(all_cites):
    matches = _find(all_cites, "400 So. 3d 200")
    assert len(matches) >= 1


def test_sw3d(all_cites):
    matches = _find(all_cites, "500 S.W. 3d 300")
    assert len(matches) == 1


def test_p3d(all_cites):
    matches = _find(all_cites, "150 P. 3d 200")
    assert len(matches) == 1


# --- State-specific reporters ---

def test_nd_reports(all_cites):
    matches = _find(all_cites, "50 N.D. 123")
    assert len(matches) >= 1


# --- Federal case reporters ---
# Note: normalization keeps spaces (e.g., "S. Ct.", "F. Supp. 3d", "L. Ed. 2d")

def test_us_reports(all_cites):
    matches = _find(all_cites, "505 U.S. 377")
    assert len(matches) == 1
    urls = [s.url for s in matches[0].sources]
    assert any("justia" in u for u in urls)


def test_f3d(all_cites):
    matches = _find(all_cites, "400 F.3d 500")
    assert len(matches) == 1


def test_f4th(all_cites):
    matches = _find(all_cites, "50 F.4th 100")
    assert len(matches) == 1


def test_f_supp_3d(all_cites):
    matches = _find(all_cites, "500 F. Supp. 3d 100")
    assert len(matches) >= 1


def test_s_ct(all_cites):
    matches = _find(all_cites, "140 S. Ct. 1731")
    assert len(matches) == 1


def test_l_ed_2d(all_cites):
    matches = _find(all_cites, "120 L. Ed. 2d 500")
    assert len(matches) == 1


def test_br(all_cites):
    matches = _find(all_cites, "300 B.R. 50")
    assert len(matches) == 1


def test_frd(all_cites):
    matches = _find(all_cites, "200 F.R.D. 100")
    assert len(matches) == 1


def test_fed_cl(all_cites):
    matches = _find(all_cites, "100 Fed. Cl. 50")
    assert len(matches) == 1


def test_mj(all_cites):
    matches = _find(all_cites, "75 M.J. 200")
    assert len(matches) == 1


def test_vet_app(all_cites):
    matches = _find(all_cites, "30 Vet. App. 100")
    assert len(matches) == 1


def test_tc(all_cites):
    matches = _find(all_cites, "150 T.C. 50")
    assert len(matches) == 1


# --- Parallel citations ---
# Note: In all_citation_types.txt, many citations appear both in their
# own section AND in the parallel section, so deduplication keeps the
# first occurrence. Parallel detection is tested in test_scanner.py
# and in the opinion fixture below where each citation is unique.

def test_parallel_in_isolation():
    """Parallel detection works when citations aren't deduplicated away."""
    cites = scan_text("See 585 N.W.2d 123, 2000 ND 45.")
    nw = _find(cites, "585 N.W. 2d 123")
    nd = _find(cites, "2000 ND 45")
    assert len(nw) == 1
    assert len(nd) == 1
    assert "2000 ND 45" in nw[0].parallel_cites
    assert "585 N.W. 2d 123" in nd[0].parallel_cites


# --- URL generation spot checks ---

def test_ndcc_url(all_cites):
    matches = _find(all_cites, "N.D.C.C. § 1-02-13")
    assert len(matches) >= 1
    urls = [s.url for s in matches[0].sources]
    assert any("ndlegis" in u for u in urls)


def test_nd_neutral_url(all_cites):
    matches = _find(all_cites, "2024 ND 156")
    assert len(matches) >= 1
    urls = [s.url for s in matches[0].sources]
    assert any("ndcourts" in u for u in urls)


def test_nw2d_ndcourts_search_url(all_cites):
    matches = _find(all_cites, "585 N.W. 2d 123")
    assert len(matches) >= 1
    urls = [s.url for s in matches[0].sources]
    assert any("ndcourts.gov" in u for u in urls)


def test_usc_url(all_cites):
    matches = _find(all_cites, "42 U.S.C. § 1983")
    assert len(matches) >= 1
    urls = [s.url for s in matches[0].sources]
    assert any(u for u in urls)


# ── sample_opinion.txt ──────────────────────────────────────────


@pytest.fixture(scope="module")
def opinion_cites():
    return _scan_fixture("sample_opinion.txt")


def test_opinion_finds_ndcc(opinion_cites):
    matches = _find_containing(opinion_cites, "N.D.C.C.")
    assert len(matches) >= 2


def test_opinion_finds_neutral(opinion_cites):
    nd_neutrals = [c for c in opinion_cites if "ND" in c.normalized and c.cite_type.value == "case"]
    assert len(nd_neutrals) >= 3


def test_opinion_finds_us_const(opinion_cites):
    matches = _find(opinion_cites, "U.S. Const. amend. IV")
    assert len(matches) >= 1


def test_opinion_finds_nd_const(opinion_cites):
    matches = _find(opinion_cites, "N.D. Const. art. I, § 8")
    assert len(matches) >= 1


def test_opinion_finds_nw2d(opinion_cites):
    nw = _find_containing(opinion_cites, "N.W.")
    assert len(nw) >= 3


def test_opinion_finds_us_reports(opinion_cites):
    matches = _find(opinion_cites, "392 U.S. 1")
    assert len(matches) == 1


def test_opinion_finds_s_ct(opinion_cites):
    matches = _find_containing(opinion_cites, "S. Ct.")
    assert len(matches) >= 1


def test_opinion_parallel_nd_nw(opinion_cites):
    nd_252 = _find(opinion_cites, "2013 ND 252")
    assert len(nd_252) == 1
    assert any("N.W." in p for p in nd_252[0].parallel_cites)


def test_opinion_finds_court_rules(opinion_cites):
    rules = [c for c in opinion_cites if c.cite_type.value == "court_rule"]
    assert len(rules) >= 1


def test_opinion_finds_usc_1983(opinion_cites):
    matches = _find(opinion_cites, "42 U.S.C. § 1983")
    assert len(matches) >= 1


def test_opinion_total_count(opinion_cites):
    """The sample opinion should yield a reasonable number of unique citations."""
    assert len(opinion_cites) >= 15
