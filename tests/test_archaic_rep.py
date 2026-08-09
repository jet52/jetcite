"""The archaic "Rep." reporter suffix (jetcite 2.10).

Through the 1880s-1900s the reporters were cited with a "Rep." on the end --
"62 N. W. Rep. 594".  jetcite matched none of it, which left ~2,950 citation
sites in the North Dakota corpus invisible to the graph.

The class these tests really guard is the NEIGHBOURING one: "Am. Rep.",
"Am. St. Rep.", "Misc. Rep." and friends are reporters whose canonical names
still contain "Rep.", and an over-eager optional group would shred them into
the wrong reporter. They are out of scope, and out of scope must mean
*untouched*, not *mangled*.
"""
import pytest

from jetcite import scan_text


def norms(text):
    return sorted({c.normalized for c in scan_text(text)})


# ------------------------------------------------- archaic suffix, first series

@pytest.mark.parametrize("text,want", [
    ("62 N. W. Rep. 594", "62 N.W. 594"),
    ("55 N.W. Rep. 580", "55 N.W. 580"),
    ("12 N. E. Rep. 866", "12 N.E. 866"),
    ("17 S. W. Rep. 644", "17 S.W. 644"),
    ("3 S. E. Rep. 349", "3 S.E. 349"),
    ("1 So. Rep. 140", "1 So. 140"),
    ("4 N. D. Rep. 452", "4 N.D. 452"),
])
def test_archaic_suffix_normalizes_to_the_modern_reporter(text, want):
    assert want in norms(text)


# ------------------------------------------- archaic NAMES the abbrev can't reach

@pytest.mark.parametrize("text,want", [
    ("36 Pac. Rep. 24", "36 P. 24"),       # `P\.` cannot reach the "P" of "Pac."
    ("17 Atl. Rep. 609", "17 A. 609"),     # `A\.` cannot reach the "A" of "Atl."
    ("24 At. Rep. 685", "24 A. 685"),
    ("5 South. Rep. 620", "5 So. 620"),
    ("82 Fed. Rep. 277", "82 F. 277"),     # `F\.` cannot reach the "F" of "Fed."
    ("112 U. S. Rep. 377", "112 U.S. 377"),
    ("17 Sup. Ct. Rep. 748", "17 S. Ct. 748"),
])
def test_archaic_reporter_names(text, want):
    assert want in norms(text)


@pytest.mark.parametrize("text,want", [
    ("16 Pac. 931", "16 P. 931"),
    ("1 Sup. Ct. 389", "1 S. Ct. 389"),
    ("15 Atl. 166", "15 A. 166"),
    ("22 At. 893", "22 A. 893"),
    ("43 Fed. 333", "43 F. 333"),
    ("7 South. 51", "7 So. 51"),
])
def test_the_bare_forms_without_rep(text, want):
    """2.10.0's bug: "Rep." shipped MANDATORY on these names, on the claim that
    a bare "Pac." was prose. The corpus carries 3,585 bare "Pac.", 1,677 bare
    "Sup. Ct.", 1,005 bare "Atl.", 855 bare "Fed.", 454 bare "South."."""
    assert want in norms(text)


@pytest.mark.parametrize("text", [
    "5 Fed. Cas. 563",                      # Federal Cases, a different reporter
    "Southern Pac. Ry. Co. v. Yeagin",      # a party name, no volume
    "rule 9, Sup. Ct. Rules (74 N. W. vi)",  # a rule set, not a page
])
def test_the_digit_on_both_sides_is_what_keeps_the_bare_forms_safe(text):
    """Dropping the mandatory "Rep." is only safe because a PAGE NUMBER must
    follow. Each of these puts a reporter name or a word there instead."""
    assert norms(text) == []


def test_bare_sc_stays_south_carolina():
    """The asymmetry: "Rep." is optional on "Sup. Ct." but mandatory on "S. C.",
    because a bare "S. C." is the state. Without this, every South Carolina
    cite would silently re-point at the U.S. Supreme Court."""
    got = norms("10 S.C. 873")
    assert "10 S.C. 873" in got
    assert "10 S. Ct. 873" not in got


@pytest.mark.parametrize("text,want", [
    ("1 N.W.Rep. 691", "1 N.W. 691"),
    ("17 N.E.Rep. 147", "17 N.E. 147"),
    ("5 S.E.Rep. 383", "5 S.E. 383"),
])
def test_unspaced_rep(text, want):
    """The print sometimes closes the gap: "1 N.W.Rep. 691". The optional group
    sits before the mandatory whitespace so both spacings are reached."""
    assert want in norms(text)


def test_sc_rep_is_the_supreme_court_reporter_not_south_carolina():
    """The trap. `S.C.` is a state reporter in regional.py, and "10 S. C. Rep.
    873" is 10 S. Ct. 873 -- resolving it to South Carolina would point the
    citation at a different court in a different state."""
    got = norms("10 S. C. Rep. 873")
    assert "10 S. Ct. 873" in got
    assert "10 S.C. 873" not in got


# ------------------------------------------------------- the out-of-scope class

@pytest.mark.parametrize("text", [
    "24 Am. St. Rep. 481",     # American State Reports -- "Rep." is its NAME
    "1 Am. Rep. 11",           # American Reports
    "20 Misc. Rep. 155",       # New York Miscellaneous Reports
    "12 N. Y. St. Rep. 74",
    "24 Eng. Rep. 446",
    "19 Am. Bankr. Rep. 650",
])
def test_reporters_whose_name_contains_rep_are_left_alone(text):
    """Not supported is fine; silently becoming "24 A. 481" is not."""
    assert norms(text) == []


# ------------------------------------------------------------- no regressions

@pytest.mark.parametrize("text,want", [
    ("259 N.W.2d 621", "259 N.W.2d 621"),
    ("4 N. D. 100", "4 N.D. 100"),
    ("200 F. 100", "200 F. 100"),
    ("140 S. Ct. 1731", "140 S. Ct. 1731"),
    ("505 U.S. 377", "505 U.S. 377"),
    ("409 So. 3d 188", "409 So. 3d 188"),
    ("491 F.3d 355", "491 F.3d 355"),
])
def test_modern_forms_unchanged(text, want):
    assert want in norms(text)


def test_series_suffix_never_takes_a_rep():
    """"N.W.2d Rep." never existed. The optional group is first-series only,
    so this must not resolve to 259 N.W.2d 621 by skipping over "Rep."."""
    assert "259 N.W.2d 621" not in norms("259 N.W.2d Rep. 621")


def test_the_minkler_body_citation():
    """4 N.D. 507 -- the citation that started this: West's flattened italic run
    had glued the volume to the case name, and the archaic form did the rest."""
    text = "In the case of *Paulson*v. *Ward*, 4 N. D. 100, 58 N. W. 792, the writer"
    got = norms(text)
    assert "4 N.D. 100" in got
    assert "58 N.W. 792" in got
