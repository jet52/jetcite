"""Tests for the ND Supreme Court's Redbook supplement citation rules.

Covers the three machine-checkable rules in the supplement:

  1. Court of Appeals public-domain cites use "ND App" and share a
     year/number space with the Supreme Court's "ND" cites.
  2. The special short form — first party's name + "at" + pinpoint — used
     where "id." is unavailable but the full form appeared in the same
     paragraph ("Kuntz, at ¶ 11").
  3. A full public-domain cite gives the North Western Reporter's first page
     only; a pin cite to the reporter in that pair is improper.

Real ND App citations used below were taken from the ND opinion corpus, not
composed: 2005 ND App 7 is Kerzmann v. Burleigh County Social Services and
2007 ND App 4 is Riemers v. State (cited in 2013 ND 188).
"""

from jetcite.cache import citation_path
from jetcite.patterns.neutral import NeutralCitationMatcher
from jetcite.scanner import scan_text

# ---------------------------------------------------------------------------
# 1. Court of Appeals — "ND App"
# ---------------------------------------------------------------------------


def test_nd_app_neutral_parses():
    m = NeutralCitationMatcher()
    results = m.find_all("Johnson v. State, 2005 ND App 8, ¶ 7, 700 N.W.2d 723.")
    neutrals = [r for r in results if r.normalized.startswith("2005 ND")]
    assert len(neutrals) == 1
    assert neutrals[0].normalized == "2005 ND App 8"
    assert neutrals[0].jurisdiction == "nd"
    assert neutrals[0].components["court"] == "ND App"
    assert neutrals[0].pinpoint == "¶ 7"


def test_nd_app_uses_unspaced_cittype_in_search_url():
    """ndcourts.gov keys the Court of Appeals on citType=NDApp.

    A percent-encoded "ND%20App" returns no results (verified against
    2005 ND App 7 = Kerzmann).
    """
    m = NeutralCitationMatcher()
    (cite,) = [r for r in m.find_all("2005 ND App 7") if r.normalized.startswith("2005")]
    url = next(s.url for s in cite.sources if s.name == "ndcourts")
    assert "citType=NDApp" in url


def test_supreme_court_cite_unaffected():
    m = NeutralCitationMatcher()
    (cite,) = m.find_all("2017 ND 119")
    assert cite.normalized == "2017 ND 119"
    assert cite.components["court"] == "ND"
    url = next(s.url for s in cite.sources if s.name == "ndcourts")
    assert "citType=ND&" in url


def test_nd_app_and_supreme_court_do_not_collide_in_refs_cache():
    """2005 ND 7 and 2005 ND App 7 are different cases — different paths."""
    m = NeutralCitationMatcher()
    (sc,) = m.find_all("2005 ND 7")
    (app,) = [r for r in m.find_all("2005 ND App 7") if r.normalized.startswith("2005")]
    sc_path, app_path = citation_path(sc), citation_path(app)
    assert sc_path != app_path
    assert str(sc_path) == "opin/ND/2005/2005ND7.md"
    assert str(app_path) == "opin/NDApp/2005/2005NDApp7.md"


# ---------------------------------------------------------------------------
# 2. Special short form — "Kuntz, at ¶ 11"
# ---------------------------------------------------------------------------


def _pins(text):
    return {c.normalized: c for c in scan_text(text, include_pin_cites=True)
            if c.is_pin_cite}


def test_name_at_paragraph_short_form_resolves_to_neutral_parent():
    text = (
        "Kuntz v. State, 2019 ND 46, ¶ 11, 923 N.W.2d 513. "
        "Another v. Case, 2020 ND 5, ¶ 3, 1 N.W.3d 2. "
        "Kuntz, at ¶ 11."
    )
    pin = _pins(text)["Kuntz, at ¶ 11"]
    assert pin.parent_normalized == "2019 ND 46"
    assert pin.pin_paragraph == "11"


def test_name_at_page_short_form_still_resolves():
    """The reporter variant ("Falcon, at 836") already worked; keep it working."""
    text = (
        "State v. Falcon, 546 N.W.2d 835, 836 (N.D. 1996). "
        "Other v. Case, 400 N.W.2d 1 (N.D. 1987). "
        "Falcon, at 836."
    )
    pin = _pins(text)["Falcon, at 836"]
    assert pin.parent_normalized == "546 N.W.2d 835"
    assert pin.pin_page == "836"


def test_name_at_paragraph_short_form_resolves_to_nd_app_parent():
    text = (
        "Riemers v. State, 2007 ND App 4, ¶ 8, 739 N.W.2d 248. "
        "Another v. Case, 2008 ND 1, ¶ 2, 1 N.W.2d 3. "
        "Riemers, at ¶ 8."
    )
    pin = _pins(text)["Riemers, at ¶ 8"]
    assert pin.parent_normalized == "2007 ND App 4"
    assert pin.pin_paragraph == "8"


def test_id_at_paragraph_form():
    text = "State v. Erickson, 2018 ND 133, ¶ 7, 911 N.W.2d 913. Id. at ¶ 7."
    pin = _pins(text)["Id. at ¶ 7"]
    assert pin.parent_normalized == "2018 ND 133"
    assert pin.pin_paragraph == "7"


# ---------------------------------------------------------------------------
# 3. No pin cite to the reporter in a public-domain parallel
# ---------------------------------------------------------------------------


def _flagged(text):
    return [c.normalized for c in scan_text(text) if c.improper_parallel_pincite]


def test_reporter_pincite_in_parallel_is_flagged():
    text = "Miller v. MedCenter One, 1997 ND 231, ¶ 10, 571 N.W.2d 358, 360."
    assert _flagged(text) == ["571 N.W.2d 358"]


def test_parallel_without_reporter_pincite_is_clean():
    text = "Miller v. MedCenter One, 1997 ND 231, ¶ 10, 571 N.W.2d 358."
    assert _flagged(text) == []


def test_pre_1997_reporter_pincite_is_not_flagged():
    """Before the public-domain form, the reporter pin cite is the correct form."""
    text = "Gissel v. Kenmare Twp., 512 N.W.2d 470, 477 (N.D. 1994)."
    assert _flagged(text) == []
    text = "Koller v. State, 19 N.W.2d 822, 823 (N.D. 1945)."
    assert _flagged(text) == []


def test_nd_app_parallel_pincite_is_flagged():
    text = "Johnson v. State, 2005 ND App 8, ¶ 7, 700 N.W.2d 723, 726."
    assert _flagged(text) == ["700 N.W.2d 723"]


def test_page_range_pincite_is_flagged():
    text = "State v. Bernstein, 2005 ND App 6, ¶¶ 23-24, 697 N.W.2d 451, 455-56."
    assert _flagged(text) == ["697 N.W.2d 451"]


def test_flag_is_scoped_to_nd_pairs():
    """Other states' medium-neutral conventions are not jetcite's to assert."""
    text = "State v. Smith, 2018-Ohio-4635, ¶ 12, 120 N.E.3d 100, 105."
    assert _flagged(text) == []


def test_flag_survives_the_legacy_dict_conversion():
    """Consumers read to_legacy_dict(), not to_dict() — the flag must cross both."""
    from pathlib import Path

    from jetcite.legacy import to_legacy_dict

    text = "Johnson v. State, 2005 ND App 8, ¶ 7, 700 N.W.2d 723, 726."
    cites = scan_text(text)
    entries = [to_legacy_dict(c, Path("/nonexistent")) for c in cites]
    flagged = [e["normalized"] for e in entries if e.get("improper_parallel_pincite")]
    assert flagged == ["700 N.W.2d 723"]


def test_nd_app_legacy_entry_carries_distinct_local_path():
    from pathlib import Path

    from jetcite.legacy import to_legacy_dict

    (app,) = [c for c in scan_text("2005 ND App 7") if c.normalized.startswith("2005")]
    entry = to_legacy_dict(app, Path("/refs"))
    assert entry["local_path"] == "/refs/opin/NDApp/2005/2005NDApp7.md"
