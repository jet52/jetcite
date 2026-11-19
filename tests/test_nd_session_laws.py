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
    "1905 Minn. Laws ch. 34",
    "Minn. Laws 1905, ch. 34",
    "Comp. Laws 1913, c. 5",                           # a compilation, not a session
    "1925 Supplement, Sec. 2202",                      # "c." is not the tail of "Sec."
    "chapter 279, Laws of 1833",                       # before Dakota Territory existed
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


# ---- prose forms: no state named --------------------------------------------

@pytest.mark.parametrize("text, norms", [
    ("chapter 67 of the Session Laws of 1897", ["1897 N.D. Sess. Laws ch. 67"]),
    ("Laws of 1907, chapter 58", ["1907 N.D. Sess. Laws ch. 58"]),
    ("the statute (chapter 189, Laws 1907) under which", ["1907 N.D. Sess. Laws ch. 189"]),
    ("section 75, c. 62, Laws 1890) reads", ["1890 N.D. Sess. Laws ch. 62"]),
    ("See Laws 1919, c. 88) provide", ["1919 N.D. Sess. Laws ch. 88"]),
    ("Sess. Laws 1923, c. 215.", ["1923 N.D. Sess. Laws ch. 215"]),
    ("Laws 1887, p. 39, c. 11", ["1887 N.D. Sess. Laws ch. 11"]),
    ("chapter 223, Session Laws of North Dakota for the year 1919, relating",
     ["1919 N.D. Sess. Laws ch. 223"]),
    ("Chapter 357, Session Laws of North Dakota for 1961, was", ["1961 N.D. Sess. Laws ch. 357"]),
    ("2009 Sess. Laws ch. 637", ["2009 N.D. Sess. Laws ch. 637"]),
    ("N.D. Session Laws 1935, ch. 174", ["1935 N.D. Sess. Laws ch. 174"]),
    # a list is one citation per chapter, and the next list is not read backwards
    ("chapters 91 and 93 of the Laws of 1921, chapters 179 and 299 of the Laws of 1923",
     ["1921 N.D. Sess. Laws ch. 91", "1921 N.D. Sess. Laws ch. 93",
      "1923 N.D. Sess. Laws ch. 179", "1923 N.D. Sess. Laws ch. 299"]),
    # "Laws 1889" in prose is the last territorial session
    ("when chapter 93, Laws 1889, was enacted", ["1889 Dakota Terr. Sess. Laws ch. 93"]),
])
def test_prose_forms(text, norms):
    got = M.find_all(text)
    assert [c.normalized for c in got] == norms
    assert all(c.components["form"] == "prose" for c in got) or text.startswith("N.D.")


def test_prose_section_pinpoint_and_reporter_form_flag():
    (c,) = M.find_all("Laws 1931, c. 251, § 2. The plaintiff")
    assert (c.normalized, c.pinpoint, c.components["form"]) == ("1931 N.D. Sess. Laws ch. 251", "§ 2", "prose")
    (c,) = M.find_all("2019 N.D. Sess. Laws ch. 404")
    assert c.components["form"] == "reporter" and c.components["territorial"] is False


@pytest.mark.parametrize("text", [
    "under the Minnesota workmen's compensation statute (Laws 1921, c. 82, § 15)",
    "section 6036, Revised Codes Mont. 1921, as amended by Laws 1923, c. 9, analogous",
    "In 1907 the Legislature of Oregon enacted a comprehensive law, chapter 226, Laws 1907, making",
    "the hawkers' act of 1889 of that state (Laws 1889, c. 298) was held valid",
    "Section 18 of chapter 209, Laws of 1907 of Washington, being their primary law",
    "Section 21, c. 89, Laws 1927 of the state of Montana, which",
])
def test_prose_form_of_another_jurisdiction_is_refused(text):
    assert M.find_all(text) == []


@pytest.mark.parametrize("text, norm", [
    # a foreign CASE beside a North Dakota statute
    ("Riehl v. San Jose, 101 Cal. 442, 35 Pac. 1013. The question is whether article 18 of "
     "chapter 62 of the Laws of 1905 is valid", "1905 N.D. Sess. Laws ch. 62"),
    ("Long v. Culp, 14 Kan. 412. The first paragraph in subdivision (g), Section 37, "
     "Chapter 192, Laws 1919, was", "1919 N.D. Sess. Laws ch. 192"),
    # the state named is in the sentence before
    ("charges were pending against him in Minnesota. The carrying of concealed weapons is "
     "made a felony. Chapter 83, Laws of 1915.", "1915 N.D. Sess. Laws ch. 83"),
    # North Dakota named last, or in the citation itself, or straight after it
    ("found in Kansas, Minnesota, Iowa, and in North Dakota since the passage of chapter 132, "
     "Laws 1890, and", "1890 N.D. Sess. Laws ch. 132"),
    ("the South Dakota law was identical with Section 30, ch. 126, Laws of North Dakota 1897, which",
     "1897 N.D. Sess. Laws ch. 126"),
    ("Lincoln, Neb., for respondents, declaring Chapter 303 of the Session Laws of 1955 of North "
     "Dakota unconstitutional", "1955 N.D. Sess. Laws ch. 303"),
    # the federal Constitution or a federal act nearby is not another state's laws
    ("the Fourteenth Amendment to the Constitution of the United States by chapter 179, Laws 1917 "
     "(sections 5941a1", "1917 N.D. Sess. Laws ch. 179"),
])
def test_prose_form_kept_beside_a_foreign_name(text, norm):
    assert [c.normalized for c in M.find_all(text)] == [norm]


def test_prose_positions_index_the_text():
    text = "as amended by chapter 96, Session Laws 1969. The Board"
    (c,) = M.find_all(text)
    assert text[c.position:c.position + len(c.raw_text)] == c.raw_text == "chapter 96, Session Laws 1969"
