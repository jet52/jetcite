"""Tests for the legacy JSON format module."""

from pathlib import Path

from jetcite.legacy import (
    AUTHORITY_TYPES,
    CASE_TYPES,
    FEDERAL_REPORTERS,
    add_parallel_info,
    legacy_cite_type,
    primary_url,
    search_hint,
    to_legacy_dict,
)
from jetcite.models import Citation, CitationType, Source


# ── Helpers ──────────────────────────────────────────────────────


def _nd_neutral():
    return Citation(
        raw_text="2024 ND 156", cite_type=CitationType.CASE,
        jurisdiction="nd", normalized="2024 ND 156",
        components={"year": "2024", "number": "156"},
        sources=[Source("ndcourts", "https://example.com/2024ND156")],
    )


def _ohio_neutral():
    return Citation(
        raw_text="2022-Ohio-4635", cite_type=CitationType.CASE,
        jurisdiction="oh", normalized="2022-Ohio-4635",
        components={"year": "2022", "number": "4635"},
        sources=[Source("courtlistener", "https://courtlistener.com/...")],
    )


def _nw2d():
    return Citation(
        raw_text="585 N.W.2d 123", cite_type=CitationType.CASE,
        jurisdiction="us", normalized="585 N.W.2d 123",
        components={"volume": "585", "reporter": "N.W.2d", "page": "123"},
    )


def _p3d():
    return Citation(
        raw_text="478 P.3d 164", cite_type=CitationType.CASE,
        jurisdiction="us", normalized="478 P.3d 164",
        components={"volume": "478", "reporter": "P.3d", "page": "164"},
    )


def _us_reports():
    return Citation(
        raw_text="505 U.S. 377", cite_type=CitationType.CASE,
        jurisdiction="us", normalized="505 U.S. 377",
        components={"volume": "505", "reporter": "U.S.", "page": "377"},
        sources=[Source("justia", "https://supreme.justia.com/...")],
    )


def _f3d():
    return Citation(
        raw_text="410 F.3d 438", cite_type=CitationType.CASE,
        jurisdiction="us", normalized="410 F.3d 438",
        components={"volume": "410", "reporter": "F.3d", "page": "438"},
    )


def _ndcc():
    return Citation(
        raw_text="N.D.C.C. § 12.1-32-01", cite_type=CitationType.STATUTE,
        jurisdiction="nd", normalized="N.D.C.C. § 12.1-32-01",
        components={"title": "12.1", "chapter": "32", "section": "01"},
    )


def _usc():
    return Citation(
        raw_text="42 U.S.C. § 1983", cite_type=CitationType.STATUTE,
        jurisdiction="us", normalized="42 U.S.C. § 1983",
        components={"title": "42", "section": "1983"},
    )


def _ndac():
    return Citation(
        raw_text="N.D.A.C. § 43-02-05-01", cite_type=CitationType.REGULATION,
        jurisdiction="nd", normalized="N.D.A.C. § 43-02-05-01",
        components={"part1": "43", "part2": "02", "part3": "05", "part4": "01"},
    )


def _cfr():
    return Citation(
        raw_text="40 C.F.R. § 52.21", cite_type=CitationType.REGULATION,
        jurisdiction="us", normalized="40 C.F.R. § 52.21",
        components={"title": "40", "section": "52.21"},
    )


def _nd_const():
    return Citation(
        raw_text="N.D. Const. art. I, § 20", cite_type=CitationType.CONSTITUTION,
        jurisdiction="nd", normalized="N.D. Const. art. I, § 20",
        components={"article": "I", "section": "20"},
    )


def _us_const_amend():
    return Citation(
        raw_text="U.S. Const. amend. XIV", cite_type=CitationType.CONSTITUTION,
        jurisdiction="us", normalized="U.S. Const. amend. XIV",
        components={"amendment": "XIV"},
    )


def _nd_rule():
    return Citation(
        raw_text="N.D.R.Civ.P. 56", cite_type=CitationType.COURT_RULE,
        jurisdiction="nd", normalized="N.D.R.Civ.P. 56",
        components={"rule_set": "ndrcivp", "parts": ["56"]},
    )


def _federal_rule():
    return Citation(
        raw_text="Fed. R. Civ. P. 12(b)(6)", cite_type=CitationType.COURT_RULE,
        jurisdiction="us", normalized="Fed. R. Civ. P. 12(b)(6)",
        components={"rule_set": "frcp", "rule_number": "12", "subsection": "(b)(6)"},
    )


# ── legacy_cite_type ─────────────────────────────────────────────


def test_nd_neutral_is_neutral_cite():
    assert legacy_cite_type(_nd_neutral()) == "neutral_cite"


def test_ohio_neutral_is_neutral_cite():
    assert legacy_cite_type(_ohio_neutral()) == "neutral_cite"


def test_nw2d_is_regional_reporter():
    assert legacy_cite_type(_nw2d()) == "regional_reporter"


def test_p3d_is_regional_reporter():
    assert legacy_cite_type(_p3d()) == "regional_reporter"


def test_us_reports_is_us_supreme_court():
    assert legacy_cite_type(_us_reports()) == "us_supreme_court"


def test_f3d_is_federal_reporter():
    assert legacy_cite_type(_f3d()) == "federal_reporter"


def test_ndcc_is_statute():
    assert legacy_cite_type(_ndcc()) == "statute"


def test_usc_is_statute():
    assert legacy_cite_type(_usc()) == "statute"


def test_ndac_is_regulation():
    assert legacy_cite_type(_ndac()) == "regulation"


def test_cfr_is_regulation():
    assert legacy_cite_type(_cfr()) == "regulation"


def test_nd_const_is_constitution():
    assert legacy_cite_type(_nd_const()) == "constitution"


def test_us_const_is_constitution():
    assert legacy_cite_type(_us_const_amend()) == "constitution"


def test_nd_rule_is_court_rule():
    assert legacy_cite_type(_nd_rule()) == "court_rule"


def test_federal_rule_is_court_rule():
    assert legacy_cite_type(_federal_rule()) == "court_rule"


def test_statute_chapter():
    cite = Citation(
        raw_text="N.D.C.C. ch. 12.1-32", cite_type=CitationType.STATUTE,
        jurisdiction="nd", normalized="N.D.C.C. ch. 12.1-32",
        components={"title": "12.1", "chapter": "32"},
    )
    assert legacy_cite_type(cite) == "statute_chapter"


# ── search_hint ──────────────────────────────────────────────────


def test_hint_nd_neutral():
    assert search_hint(_nd_neutral()) == "2024ND156"


def test_hint_ohio_neutral():
    assert search_hint(_ohio_neutral()) == "2022OH4635"


def test_hint_ndcc():
    assert search_hint(_ndcc()) == "12.1-32-01"


def test_hint_usc():
    assert search_hint(_usc()) == "42 US 1983"


def test_hint_ndac():
    assert search_hint(_ndac()) == "43-02-05-01"


def test_hint_cfr():
    assert search_hint(_cfr()) == "40 CFR 52.21"


def test_hint_nd_const():
    assert search_hint(_nd_const()) == "article I section 20"


def test_hint_us_const_amend():
    assert search_hint(_us_const_amend()) == "amendment XIV"


def test_hint_us_supreme_court():
    assert search_hint(_us_reports()) == "505 US 377"


def test_hint_regional_reporter():
    assert search_hint(_nw2d()) == "585 N.W.2d 123"


def test_hint_federal_reporter():
    assert search_hint(_f3d()) == "410 F.3d 438"


def test_hint_court_rule():
    assert search_hint(_nd_rule()) == "56"


# ── to_legacy_dict ───────────────────────────────────────────────


def test_to_legacy_dict_fields(tmp_path):
    cite = _nd_neutral()
    d = to_legacy_dict(cite, tmp_path)
    assert d["cite_text"] == "2024 ND 156"
    assert d["cite_type"] == "neutral_cite"
    assert d["normalized"] == "2024 ND 156"
    assert d["jurisdiction"] == "nd"
    assert d["url"] is not None
    assert d["search_hint"] == "2024ND156"
    assert d["local_path"] is not None
    assert d["local_exists"] is False


def test_to_legacy_dict_local_exists(tmp_path):
    cite = _nd_neutral()
    # Pre-populate the cache
    path = tmp_path / "opin/ND/2024/2024ND156.md"
    path.parent.mkdir(parents=True)
    path.write_text("opinion")

    d = to_legacy_dict(cite, tmp_path)
    assert d["local_exists"] is True
    assert d["local_path"] == str(path)


# ── primary_url ──────────────────────────────────────────────────


def test_primary_url_skips_local():
    cite = _nd_neutral()
    cite.sources.insert(0, Source("local", "file:///tmp/test.md"))
    assert primary_url(cite) == "https://example.com/2024ND156"


def test_primary_url_no_sources():
    cite = Citation(
        raw_text="x", cite_type=CitationType.CASE,
        jurisdiction="us", normalized="x", components={}, sources=[],
    )
    assert primary_url(cite) is None


# ── add_parallel_info ────────────────────────────────────────────


def test_parallel_info(tmp_path):
    cite1 = _nd_neutral()
    cite1.parallel_cites = ["585 N.W.2d 123"]
    cite2 = _nw2d()

    entries = [to_legacy_dict(cite1, tmp_path), to_legacy_dict(cite2, tmp_path)]
    add_parallel_info(entries, [cite1, cite2])

    assert entries[0].get("parallel_cite") == "585 N.W.2d 123"


# ── constants ────────────────────────────────────────────────────


def test_case_types_complete():
    assert "neutral_cite" in CASE_TYPES
    assert "regional_reporter" in CASE_TYPES
    assert "us_supreme_court" in CASE_TYPES
    assert "federal_reporter" in CASE_TYPES


def test_authority_types_complete():
    assert "statute" in AUTHORITY_TYPES
    assert "regulation" in AUTHORITY_TYPES
    assert "constitution" in AUTHORITY_TYPES
    assert "court_rule" in AUTHORITY_TYPES
