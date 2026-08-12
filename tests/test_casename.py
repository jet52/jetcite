"""Tests for antecedent case-name extraction."""

import pytest

from jetcite.casename import extract_antecedent_name
from jetcite.scanner import scan_text


def _name_at(text: str, cite: str) -> str | None:
    return extract_antecedent_name(text, text.find(cite))


# ── extract_antecedent_name: full adversary captions ──────────────

def test_full_caption_basic():
    assert _name_at("See Boedecker v. St. Alexius Hospital, 298 N.W.2d 372.",
                    "298 N.W.2d 372") == "Boedecker v. St. Alexius Hospital"


def test_full_caption_abbreviated_party():
    assert _name_at("(citing Boedecker v. St. Alexius Hosp., 298 N.W.2d 372,",
                    "298 N.W.2d 372") == "Boedecker v. St. Alexius Hosp."


def test_full_caption_after_sentence():
    assert _name_at("would be an advisory opinion. Boedecker v. St. Alexius Hospital, 298 N.W.2d 372 (",
                    "298 N.W.2d 372") == "Boedecker v. St. Alexius Hospital"


def test_full_caption_with_markdown_italics():
    # markdown emphasis markers around the signal + name, no space before cite
    assert _name_at("the district court. *See Boedecker v. St. Alexius Hospital,*298 N.W.2d 372,",
                    "298 N.W.2d 372") == "Boedecker v. St. Alexius Hospital"


def test_state_v_party():
    assert _name_at("The rule from State v. Hagensen, 498 N.W.2d 615, applies.",
                    "498 N.W.2d 615") == "State v. Hagensen"


def test_company_and_abbreviations():
    assert _name_at("See Reimers Seed Co. v. Stedman, 465 N.W.2d 175.",
                    "465 N.W.2d 175") == "Reimers Seed Co. v. Stedman"


def test_leading_signal_stripped():
    # "See" must not be folded into the name
    assert _name_at("blah. Cf. Lough v. White, 100 N.W. 1084.",
                    "100 N.W. 1084") == "Lough v. White"


# ── procedural captions ───────────────────────────────────────────

def test_procedural_in_re_estate():
    assert _name_at("We discussed this in In re Estate of Papineau, 396 N.W.2d 735.",
                    "396 N.W.2d 735") == "In re Estate of Papineau"


def test_procedural_matter_of():
    assert _name_at("As held in Matter of Gessler, 419 N.W.2d 541, the court...",
                    "419 N.W.2d 541") == "Matter of Gessler"


def test_procedural_in_re_surname():
    assert _name_at("See In re McMahon, 298 N.W.2d 372.",
                    "298 N.W.2d 372") == "In re McMahon"


# ── short form ────────────────────────────────────────────────────

def test_short_form_surname():
    assert _name_at("as we held in Boedecker, 298 N.W.2d at 374",
                    "298 N.W.2d at 374") == "Boedecker"


# ── negative cases (no governing name) ────────────────────────────

def test_no_name_standalone():
    assert _name_at("Standing alone 100 N.W. 1084 with no name.", "100 N.W. 1084") is None


def test_no_name_lowercase_lead_in():
    assert _name_at("the statute codified at 298 N.W.2d 372", "298 N.W.2d 372") is None


def test_no_name_after_bare_signal():
    assert _name_at("blah blah. See 298 N.W.2d 372.", "298 N.W.2d 372") is None


def test_position_zero_returns_none():
    assert extract_antecedent_name("298 N.W.2d 372 leads the text", 0) is None


def test_short_form_rejects_signal_word():
    # "Court" alone is not a case name
    assert _name_at("This Court, 298 N.W.2d 372", "298 N.W.2d 372") is None


# ── integration through scan_text ─────────────────────────────────

def test_scan_text_populates_antecedent_name():
    text = "We follow Boedecker v. St. Alexius Hospital, 298 N.W.2d 372 (N.D. 1980)."
    cites = scan_text(text, resolve=False)
    c = next(c for c in cites if c.normalized == "298 N.W.2d 372")
    assert c.antecedent_name == "Boedecker v. St. Alexius Hospital"


def test_scan_text_parallel_inherits_name():
    # Name precedes the neutral cite; the parallel N.W.3d cite should inherit it.
    text = "See Tracey v. Tracey, 2023 ND 219, 998 N.W.2d 100."
    cites = scan_text(text, resolve=False)
    nd = next(c for c in cites if c.normalized == "2023 ND 219")
    nw = next(c for c in cites if "N.W." in c.normalized)
    assert nd.antecedent_name == "Tracey v. Tracey"
    assert nw.antecedent_name == "Tracey v. Tracey"


def test_scan_text_does_not_cross_prior_cite():
    # The second, distinct case's name must not bleed onto the first cite.
    text = "Smith v. Jones, 100 N.W. 1084; Doe v. Roe, 200 N.W. 500."
    cites = scan_text(text, resolve=False)
    c1 = next(c for c in cites if c.normalized == "100 N.W. 1084")
    c2 = next(c for c in cites if c.normalized == "200 N.W. 500")
    assert c1.antecedent_name == "Smith v. Jones"
    assert c2.antecedent_name == "Doe v. Roe"


def test_to_dict_includes_name_when_present():
    text = "See State v. Hagensen, 498 N.W.2d 615."
    c = next(c for c in scan_text(text, resolve=False) if c.normalized == "498 N.W.2d 615")
    assert c.to_dict()["antecedent_name"] == "State v. Hagensen"


# ---------------------------------------------------------------------------
# Commas inside party names
#
# A party name may legitimately contain a comma before a corporate or
# generational suffix. The name pattern joined words on whitespace alone, so
# any such comma truncated the match: "Williamson v. Lee Optical of Okla.,
# Inc." came back as "Inc.", and a sidebar grouping cites by name showed a
# heading reading only "Inc."
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("The rule receded. Williamson v. Lee Optical of Okla., Inc., 348 U.S. 483, 491 (1955).",
     "Williamson v. Lee Optical of Okla., Inc."),
    ("See Harrison v. PPG Indus., Inc., 446 U.S. 578, 602 (1980).",
     "Harrison v. PPG Indus., Inc."),
    ("See Bellemare v. Gateway Builders, Inc., 420 N.W.2d 733 (N.D. 1988).",
     "Bellemare v. Gateway Builders, Inc."),
    # Suffix on the *first* party, before the " v. ".
    ("See Hamich, Inc. v. State ex rel. Clayburgh, 1997 ND 110, 564 N.W.2d 640.",
     "Hamich, Inc. v. State ex rel. Clayburgh"),
    ("See Snyder's Drug Stores, Inc. v. N.D. State Bd. of Pharmacy, 219 N.W.2d 140.",
     "Snyder's Drug Stores, Inc. v. N.D. State Bd. of Pharmacy"),
    # Two suffix-bearing tokens in one caption.
    ("See Best Products Co., Inc. v. Spaeth, 461 N.W.2d 91 (N.D. 1990).",
     "Best Products Co., Inc. v. Spaeth"),
    ("See First Interstate Bank of Fargo, N.A. v. Larson, 475 N.W.2d 538 (N.D. 1991).",
     "First Interstate Bank of Fargo, N.A. v. Larson"),
    ("See Anderson, Jr. v. Bank, 100 N.W.2d 1 (N.D. 1960).",
     "Anderson, Jr. v. Bank"),
])
def test_comma_suffix_stays_in_party_name(text, expected):
    c = next(c for c in scan_text(text, resolve=False) if not c.is_pin_cite)
    assert c.antecedent_name == expected


def test_comma_allowance_does_not_reach_into_prior_sentence():
    """The suffix list is the guard rail.

    A blanket "comma then capitalized word" rule would capture "Smith," here.
    Only recognized corporate/generational suffixes may follow a comma.
    """
    text = "In Smith, Jones v. Brown, 100 N.W.2d 1 (N.D. 1960)."
    c = next(c for c in scan_text(text, resolve=False) if not c.is_pin_cite)
    assert c.antecedent_name == "Jones v. Brown"


def test_ordinary_names_unaffected():
    for text, expected in [
        ("See Herr v. Rudolf, 25 N.W.2d 916 (N.D. 1947).", "Herr v. Rudolf"),
        ("accord Beleal v. N. Pac. Ry. Co., 108 N.W. 33 (N.D. 1906).",
         "Beleal v. N. Pac. Ry. Co."),
        ("See Dickie v. Farmers Union Oil Co. of LaMoure, 2000 ND 111.",
         "Dickie v. Farmers Union Oil Co. of LaMoure"),
    ]:
        c = next(c for c in scan_text(text, resolve=False) if not c.is_pin_cite)
        assert c.antecedent_name == expected
