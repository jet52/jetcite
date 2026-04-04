"""Tests for federal court rule citation patterns.

Uses real citations found in North Dakota Supreme Court opinions.
"""

from jetcite.patterns.federal_rules import FederalRuleMatcher


# ── Fed. R. Civ. P. (full form) ──────────────────────────────────


def test_frcp_full_form():
    """Fed. R. Civ. P. 60 — from 2020 ND 114."""
    m = FederalRuleMatcher()
    results = m.find_all("Fed. R. Civ. P. 60")
    assert len(results) == 1
    assert results[0].normalized == "Fed. R. Civ. P. 60"
    assert results[0].components["rule_set"] == "frcp"
    assert results[0].components["rule_number"] == "60"


def test_frcp_with_subsection():
    """Fed. R. Civ. P. 12(b)(6) — from 2020 ND 98."""
    m = FederalRuleMatcher()
    results = m.find_all("Fed. R. Civ. P. 12(b)(6)")
    assert len(results) == 1
    assert results[0].normalized == "Fed. R. Civ. P. 12(b)(6)"
    assert results[0].components["rule_number"] == "12"
    assert results[0].components["subsection"] == "(b)(6)"


def test_frcp_rule_56():
    """Fed. R. Civ. P. 56 — summary judgment, very common."""
    m = FederalRuleMatcher()
    results = m.find_all("Fed. R. Civ. P. 56")
    assert len(results) == 1
    assert results[0].components["rule_number"] == "56"


def test_frcp_rule_50():
    """Fed. R. Civ. P. 50 — from 2020 ND 98."""
    m = FederalRuleMatcher()
    results = m.find_all("Fed. R. Civ. P. 50")
    assert len(results) == 1
    assert results[0].components["rule_number"] == "50"


# ── Fed. R. Crim. P. ─────────────────────────────────────────────


def test_frcrp_full_form():
    m = FederalRuleMatcher()
    results = m.find_all("Fed. R. Crim. P. 29")
    assert len(results) == 1
    assert results[0].normalized == "Fed. R. Crim. P. 29"
    assert results[0].components["rule_set"] == "frcrp"


# ── Fed. R. Evid. ────────────────────────────────────────────────


def test_fre_full_form():
    m = FederalRuleMatcher()
    results = m.find_all("Fed. R. Evid. 403")
    assert len(results) == 1
    assert results[0].normalized == "Fed. R. Evid. 403"
    assert results[0].components["rule_set"] == "fre"


def test_fre_rule_801():
    m = FederalRuleMatcher()
    results = m.find_all("Fed. R. Evid. 801")
    assert len(results) == 1
    assert results[0].components["rule_number"] == "801"


# ── Fed. R. App. P. ──────────────────────────────────────────────


def test_frap_full_form():
    """Fed. R. App. P. 2 — from 2024 ND opinions."""
    m = FederalRuleMatcher()
    results = m.find_all("Fed. R. App. P. 2")
    assert len(results) == 1
    assert results[0].components["rule_set"] == "frap"


# ── Fed. R. Bankr. P. ────────────────────────────────────────────


def test_frbp_full_form():
    m = FederalRuleMatcher()
    results = m.find_all("Fed. R. Bankr. P. 7001")
    assert len(results) == 1
    assert results[0].components["rule_set"] == "frbp"


# ── Abbreviation forms ───────────────────────────────────────────


def test_frcp_abbreviation():
    m = FederalRuleMatcher()
    results = m.find_all("FRCP 12(b)(6)")
    assert len(results) == 1
    assert results[0].normalized == "Fed. R. Civ. P. 12(b)(6)"
    assert results[0].components["rule_set"] == "frcp"


def test_fre_abbreviation():
    m = FederalRuleMatcher()
    results = m.find_all("FRE 403")
    assert len(results) == 1
    assert results[0].normalized == "Fed. R. Evid. 403"


def test_frap_abbreviation():
    m = FederalRuleMatcher()
    results = m.find_all("FRAP 28")
    assert len(results) == 1
    assert results[0].normalized == "Fed. R. App. P. 28"


def test_frcrp_abbreviation():
    m = FederalRuleMatcher()
    results = m.find_all("FRCrP 29")
    assert len(results) == 1
    assert results[0].normalized == "Fed. R. Crim. P. 29"


# ── URL generation ───────────────────────────────────────────────


def test_frcp_url():
    m = FederalRuleMatcher()
    results = m.find_all("Fed. R. Civ. P. 12(b)(6)")
    assert results[0].sources[0].name == "cornell"
    assert "frcivp" in results[0].sources[0].url
    assert "rule_12" in results[0].sources[0].url


def test_fre_url():
    m = FederalRuleMatcher()
    results = m.find_all("Fed. R. Evid. 403")
    assert "fre" in results[0].sources[0].url
    assert "rule_403" in results[0].sources[0].url


# ── Edge cases ────────────────────────────────────────────────────


def test_multiple_rules_in_text():
    m = FederalRuleMatcher()
    text = "Under Fed. R. Civ. P. 56 and Fed. R. Evid. 403, the motion was denied."
    results = m.find_all(text)
    assert len(results) == 2
    rule_sets = {r.components["rule_set"] for r in results}
    assert rule_sets == {"frcp", "fre"}
