"""North Dakota Pattern Jury Instructions (nd_jury_instructions). Forms read from the ND
opinions 2026-11-24."""
import pytest

from jetcite import scan_text
from jetcite.models import CitationType


def _ndji(text):
    return [c.normalized for c in scan_text(text, resolve=False)
            if c.cite_type == CitationType.JURY_INSTRUCTION]


@pytest.mark.parametrize("text,expected", [
    ("NDJI-Civil C-2.05", ["NDJI-Civil C-2.05"]),
    ("N.D.J.I.\N{EM DASH}Civil C-74.40", ["NDJI-Civil C-74.40"]),
    ("NDJI C - 2.80", ["NDJI-Civil C-2.80"]),
    ("N.D.J.I. K-7.13", ["NDJI-Criminal K-7.13"]),
    ("NDJI-CRIMINAL K-5.04", ["NDJI-Criminal K-5.04"]),
    ("Pattern Jury Instruction K 21.10", ["NDJI-Criminal K-21.10"]),
    ("North Dakota Pattern Jury Instruction C-70.65", ["NDJI-Civil C-70.65"]),
    ("North Dakota Pattern Jury Instruction, NDJI \N{EM DASH} Criminal K \N{EM DASH} 5.01",
     ["NDJI-Criminal K-5.01"]),
    ("N.D.J.I. Crim. No. K\N{EN DASH}15.02", ["NDJI-Criminal K-15.02"]),
    ("(quoting NDJI \N{EM DASH} Civil C-2.05).", ["NDJI-Civil C-2.05"]),
])
def test_lettered_forms(text, expected):
    assert _ndji(text) == expected


def test_a_list_after_one_name():
    assert _ndji("See NDJI C-50.50 and C-50.51; the court gave C-2.05.") == [
        "NDJI-Civil C-50.50", "NDJI-Civil C-50.51"]


def test_letterless_decimal_under_the_series_word():
    """From 2003 opinions write the current number without its letter."""
    assert _ndji("as N.D.J.I. Civ. No. 17.05 and 17.10. Also 2.05.") == [
        "NDJI-Civil C-17.05", "NDJI-Civil C-17.10"]
    assert _ndji("NDJI-Civil 50.32") == ["NDJI-Civil C-50.32"]


@pytest.mark.parametrize("text", [
    "NDJI\N{EN DASH}CIVIL 1660",                      # the numbering before the C-/K- scheme
    "N.D.J.I.Crim. No.2001",
    "Exhibit C-2.05 was received.",                    # no name before the number
    "NDJI-Civil K-1.10",                               # series word contradicts the letter
    "See also Fifth Circuit Pattern Jury Instructions Civil 11.22 (2016)",
    "Eleventh Circuit Pattern Jury Instructions Civil 4.15 (2013)",
    "South Dakota Pattern Jury Instruction 2.05",
])
def test_not_emitted(text):
    assert _ndji(text) == []


def test_components():
    c = [c for c in scan_text("N.D.J.I. Civ. No. 17.05", resolve=False)
         if c.cite_type == CitationType.JURY_INSTRUCTION][0]
    assert c.jurisdiction == "nd" and c.components == {
        "series": "civil", "letter": "C", "number": "C-17.05", "form": "series-word"}
    assert c.sources == []
