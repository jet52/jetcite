"""North Dakota Session Laws: reporter-style forms (prose forms are out of scope)."""
import pytest

from jetcite.models import CitationType
from jetcite.patterns.states.nd_session_laws import NDSessionLawMatcher, session_laws_url

M = NDSessionLawMatcher()


@pytest.mark.parametrize("text, norm, section", [
    ("See 2019 N.D. Sess. Laws ch. 404, § 2.", "2019 N.D. Sess. Laws ch. 404", "2"),
    ("1975 N.D.Sess.Laws ch. 615", "1975 N.D. Sess. Laws ch. 615", None),
    ("1987 N.D. Laws ch. 194, § 3", "1987 N.D. Sess. Laws ch. 194", "3"),
    ("N.D.Sess.Laws 1937, ch. 159", "1937 N.D. Sess. Laws ch. 159", None),
    ("S.L. 2019, ch. 404, § 4", "2019 N.D. Sess. Laws ch. 404", "4"),
    ("S.L.1905, Ch. 34", "1905 N.D. Sess. Laws ch. 34", None),
    ("S.L. 2021 (sp.), ch. 553", "2021 N.D. Sess. Laws ch. 553", None),
    ("1937 S.L., Ch. 249", "1937 N.D. Sess. Laws ch. 249", None),
    ("S.L.N.D. 1945, ch. 106", "1945 N.D. Sess. Laws ch. 106", None),
    ("Chapter 176, SLND 1947", "1947 N.D. Sess. Laws ch. 176", None),
    ("1919 N.D. Sess. Laws Spec. Sess. ch. 4", "1919 N.D. Sess. Laws Spec. Sess. ch. 4", None),
])
def test_forms(text, norm, section):
    cs = M.find_all(text)
    assert len(cs) == 1, cs
    c = cs[0]
    assert c.normalized == norm and c.cite_type is CitationType.SESSION_LAW and c.jurisdiction == "nd"
    assert c.components["section"] == section
    assert c.pinpoint == (f"§ {section}" if section else None)
    assert text[c.position:c.position + len(c.raw_text)] == c.raw_text


@pytest.mark.parametrize("text", [
    "chapter 67 of the Session Laws of 1897",          # prose: names no state
    "Laws of 1907, chapter 58",
    "1905 Minn. Laws ch. 34",
    "N.D.C.C. ch. 28-32",
    "2019 ND 404",
    "S.L. 2019",                                       # no chapter
    "2019 N.D. Sess. Laws 1234",                       # a page cite, not a chapter
])
def test_not_matched(text):
    assert M.find_all(text) == []


def test_two_in_a_sentence_and_no_double_match():
    cs = M.find_all("1983 N.D. Sess. Laws ch. 82, § 37; S.L. 1985, ch. 82, § 162.")
    assert [c.normalized for c in cs] == ["1983 N.D. Sess. Laws ch. 82", "1985 N.D. Sess. Laws ch. 82"]
    assert [c.components["section"] for c in cs] == ["37", "162"]


def test_special_flag_and_url():
    c = M.find_all("S.L. 2021 (sp.), ch. 553")[0]
    assert c.components["special"] is True and c.sources == []
    assert session_laws_url(2019) == "https://ndlegis.gov/assembly/66-2019/session-laws/sl2019.pdf"
    assert session_laws_url(1995) is None and session_laws_url(2026) is None
    assert M.find_all("2019 N.D. Sess. Laws ch. 404")[0].sources[0].url.endswith("sl2019.pdf")


def test_scanner_emits_it():
    from jetcite import scan_text
    cs = [c for c in scan_text("The section was amended. 2019 N.D. Sess. Laws ch. 404, § 2.")
          if c.cite_type is CitationType.SESSION_LAW]
    assert len(cs) == 1 and cs[0].normalized == "2019 N.D. Sess. Laws ch. 404"


def test_runs_of_chapter_first_cites_are_not_read_year_first():
    """The 2026-11-18 precision sample: three of 141 cites were mispaired, all here."""
    cs = M.find_all("See Chapter 238 S.L.1933, Chapter 277 S.L.1935, Chapter 280 S.L.1935, "
                    "Chapter 240 S.L.1937, Chapter 227 S.L.1939, Chapter 235 S.L.1939.")
    assert [c.normalized.split("Laws ")[1] + "/" + c.components["year"] for c in cs] == [
        "ch. 238/1933", "ch. 277/1935", "ch. 280/1935", "ch. 240/1937", "ch. 227/1939", "ch. 235/1939"]
    cs = M.find_all("under Chapter 238, S.L.N.D.1939, Chapter 286, S.L.N.D.1941 and Chapter 121 S.L.N.D.1943")
    assert [(c.components["year"], c.components["chapter"]) for c in cs] == [
        ("1939", "238"), ("1941", "286"), ("1943", "121")]
    # a year-first run stays year-first
    cs = M.find_all("S.L. 1983, ch. 415, S.L. 1985, ch. 100")
    assert [(c.components["year"], c.components["chapter"]) for c in cs] == [("1983", "415"), ("1985", "100")]


def test_a_code_chapter_after_the_cite_is_not_its_chapter():
    cs = M.find_all("Chapter 174, S.L. 1937, Chapter 40–45, N.D.R.C. 1943, authorizes cities")
    assert [(c.components["year"], c.components["chapter"]) for c in cs] == [("1937", "174")]
    assert M.find_all("S.L. 1937, Chapter 40-45") == []
