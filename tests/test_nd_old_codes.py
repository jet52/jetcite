"""North Dakota and Dakota Territory codes before the Century Code (1887-1943)."""
import pytest

from jetcite.models import CitationType
from jetcite.patterns.states.nd_old_codes import NDOldCodeMatcher
from jetcite.scanner import scan_text

M = NDOldCodeMatcher()


def norms(text):
    return [c.normalized for c in M.find_all(text)]


@pytest.mark.parametrize("text, expected", [
    # the Revised Code of 1943
    ("as used in Section 49–0604, NDRC 1943, providing", ["N.D.R.C. 1943 § 49-0604"]),
    ("Sec. 34—0203, RCND 1943, is", ["N.D.R.C. 1943 § 34-0203"]),
    ("Sec. 11–1114, N.D.R.C.1943. Thus", ["N.D.R.C. 1943 § 11-1114"]),
    ("Section 12–2217, N.D.R.C. of 1943, provided", ["N.D.R.C. 1943 § 12-2217"]),
    ("Section 28-2709, NDRC, 1943, was", ["N.D.R.C. 1943 § 28-2709"]),
    ("Secs. 32-2202 and 32-2217, R.C.N.D. 1943.", ["N.D.R.C. 1943 § 32-2202", "N.D.R.C. 1943 § 32-2217"]),
    ("Section 15-0812 of the North Dakota Revised Code of 1943", ["N.D.R.C. 1943 § 15-0812"]),
    # ... with no section sign: the number's shape is the sign
    ("NDRC 1943, 65–0904. In construing", ["N.D.R.C. 1943 § 65-0904"]),
    ("R.C.1943, 61–2115. On the other hand", ["N.D.R.C. 1943 § 61-2115"]),
    ("NDRC 1943, 32–0323, 32–0316, 51–0168; 2 Sutherland",
     ["N.D.R.C. 1943 § 32-0323", "N.D.R.C. 1943 § 32-0316", "N.D.R.C. 1943 § 51-0168"]),
    ("'28–0741 N.D.R.C. 1943. And further", ["N.D.R.C. 1943 § 28-0741"]),
    ("Section 40–39–07 NDCC (40–3907 NDRC 1943) provides", ["N.D.R.C. 1943 § 40-3907"]),
    # the Compiled Laws of 1913 and the 1925 Supplement
    ("See section 5841, C. L. 1913, providing", ["N.D.C.L. 1913 § 5841"]),
    ("under section 10105, C.L.1913, as amended", ["N.D.C.L. 1913 § 10105"]),
    ("sections 8599 and 8600, Comp. Laws of 1913, an", ["N.D.C.L. 1913 § 8599", "N.D.C.L. 1913 § 8600"]),
    ("section 680 of the Compiled Laws of North Dakota 1913, and", ["N.D.C.L. 1913 § 680"]),
    ("section 4567 of the Compiled Laws for 1913, three", ["N.D.C.L. 1913 § 4567"]),
    ("Sec. 8175, C.L.N.D.1913.", ["N.D.C.L. 1913 § 8175"]),
    ("section 8719 of our Code (Comp. Laws 1913), which", ["N.D.C.L. 1913 § 8719"]),
    ("Besides section 8102, Comp.Laws Supp.1925, provides", ["N.D.C.L. Supp. 1925 § 8102"]),
    ("Section 4609c4, Supp. to C.L. of 1913, provides", ["N.D.C.L. Supp. 1925 § 4609c4"]),
    ("section 2202, Supplement 1925 (section 2202, C. L. 1913, as amended",
     ["N.D.C.L. Supp. 1925 § 2202", "N.D.C.L. 1913 § 2202"]),
    ("codified as C.L.1913, § 7644 (1925 Supp.), R.C.1943, § 29-1513",
     ["N.D.C.L. Supp. 1925 § 7644", "N.D.R.C. 1943 § 29-1513"]),
    # the Revised Codes of 1905, 1899 and 1895
    ("Section 4018, R. C. 1905, provides", ["N.D.R.C. 1905 § 4018"]),
    ("section 5630, Rev. Codes 1899, as amended", ["N.D.R.C. 1899 § 5630"]),
    ("Section 1988 of the Revised Codes of 1899 provides", ["N.D.R.C. 1899 § 1988"]),
    ("section 7366 of the Revised Code of 1905 to compel", ["N.D.R.C. 1905 § 7366"]),
    ("Section 7477, R. C. N. D. 1905, reads", ["N.D.R.C. 1905 § 7477"]),
    ("Subdivision 4, § 5472, Rev. Code 1899. Counsel", ["N.D.R.C. 1899 § 5472"]),
    ("R.C. 1895, §§ 8178, 8179, 8269.  The", ["N.D.R.C. 1895 § 8178", "N.D.R.C. 1895 § 8179", "N.D.R.C. 1895 § 8269"]),
    ("section 4441, R.C.1895, which now is section 6458 C.L.1913)", ["N.D.R.C. 1895 § 4441", "N.D.C.L. 1913 § 6458"]),
    # the Compiled Laws of Dakota Territory
    ("Sections 1640, 1643, Comp. Laws 1887, authorizing", ["Dakota C.L. 1887 § 1640", "Dakota C.L. 1887 § 1643"]),
    ("the Compiled Laws of 1887 (sections 1640-1643) provided", ["Dakota C.L. 1887 § 1640", "Dakota C.L. 1887 § 1643"]),
    ("section 4886 of the Dakota Compiled Laws of 1887.", ["Dakota C.L. 1887 § 4886"]),
    # what stands between the number and the code
    ("Section 28–2702, subd. 7, NDRC 1943. It", ["N.D.R.C. 1943 § 28-2702"]),
    ("section 15–3404 and 15–3405, [**641] NDRC 1943 it is", ["N.D.R.C. 1943 § 15-3404", "N.D.R.C. 1943 § 15-3405"]),
    ("See section 784 et seq., Revised Codes of 1905. The", ["N.D.R.C. 1905 § 784"]),
    ("The predecessor of s 7655, C.L. of 1913, was s 7058, R.C. of 1905.", ["N.D.C.L. 1913 § 7655", "N.D.R.C. 1905 § 7058"]),
])
def test_forms(text, expected):
    cs = M.find_all(text)
    assert [c.normalized for c in cs] == expected
    for c in cs:
        assert c.cite_type is CitationType.STATUTE and c.jurisdiction == "nd"
    assert text[cs[0].position:cs[0].position + len(cs[0].raw_text)] == cs[0].raw_text
    for c in cs[1:]:                     # later members of a list sit on their own number
        assert c.position > cs[0].position


def test_run_is_governed_by_the_form_that_opens_it():
    assert norms("§ 6458, Comp. Laws 1913, § 5891, Rev. Codes 1905") == [
        "N.D.C.L. 1913 § 6458", "N.D.R.C. 1905 § 5891"]
    assert norms("Comp. Laws 1913, § 6458, Rev. Codes 1905, § 5891") == [
        "N.D.C.L. 1913 § 6458", "N.D.R.C. 1905 § 5891"]
    assert norms("R.C.1895, Sec. 5432, 5433, C.L.1913, Sec. 7620, 7621, N.D.R.C.1943, 28-1411, and") == [
        "N.D.R.C. 1895 § 5432", "N.D.R.C. 1895 § 5433", "N.D.C.L. 1913 § 7620", "N.D.C.L. 1913 § 7621",
        "N.D.R.C. 1943 § 28-1411"]
    # the act section belongs to the session law; the code section follows the code
    assert norms("Laws 1927, Ch. 267, Sec. 9, N.D.R.C.1943, 57-3724 of the") == ["N.D.R.C. 1943 § 57-3724"]
    assert norms("Chapter 147, section 6 (Comp.Laws Supp.1925, § 5192a6) provided") == [
        "N.D.C.L. Supp. 1925 § 5192a6"]
    assert norms("NDRC 1943, Sec. 15–5116, 1925 Supp. s. 1321a17. The") == [
        "N.D.R.C. 1943 § 15-5116", "N.D.C.L. Supp. 1925 § 1321a17"]


def test_supplement_to_the_1943_code_keeps_its_numbering():
    cs = M.find_all("Section 39-0101, 1957 Supp. NDRC 1943")
    assert [(c.normalized, c.components["supplement"]) for c in cs] == [("N.D.R.C. 1943 § 39-0101", "1957")]
    cs = M.find_all("sections 34–0106, NDRC 1943, 34–0114, NDRC 1953 Supp.")
    assert [(c.normalized, c.components["supplement"]) for c in cs] == [
        ("N.D.R.C. 1943 § 34-0106", None), ("N.D.R.C. 1943 § 34-0114", "1953")]


@pytest.mark.parametrize("text", [
    "a statute identically like section 9374, Rev. Codes 1905. State ex rel. Curtis v. Durein, 46 Kan. 695",
    "Colorado has an exact duplicate of our section 6640, R. C. 1905, in section 2033",
    "The South Dakota statute is similar to our section 10567, Comp.Laws N.D.1913.",
    "section 7224 in the South Dakota Code (Comp. Laws 1887, § 5235), and",     # the Territory's book
])
def test_a_state_named_nearby_does_not_make_the_code_foreign(text):
    assert len(M.find_all(text)) == 1


@pytest.mark.parametrize("text", [
    "section 2202, S. D. Comp. Laws 1913, was",
    "section 2202, Comp. Laws 1913 of South Dakota",
    "sections 4157 to 4165, Montana Political Code 1895.",
    "section 12, Rev. Codes Mont. 1921",
    "section 3465, Montana Rev. Codes 1895",
    "32 Stat. 847 [U. S. Comp. St. Supp. 1905, p. 599]",
    "section 5630, Rev. Codes 1907, as amended",          # not a year North Dakota published a code
    "Section 28—27—02, NDRC 1943.",                       # a Century Code number under the old label
    "Section 65—05—12, N.D.R.C.1943, was amended",
    "Sec. 42–02, NDRC 1943, governing",                   # a chapter cited as a section
    "chapter 38, R. C. 1905, the cause",                  # restarts in each sub-code
    "chapter 83 of the Penal Code, C.L. 1913",
    "N.D.C.C. § 12.1-32-01",
])
def test_not_matched(text):
    assert M.find_all(text) == []


def test_scanner_keeps_the_neighbours():
    text = ("Sec. 173, Constitution, Sec. 11-1002, NDRC 1943. See N.D.C.C. § 28-32-19; "
            "ch. 176, S.L. 1947; section 5841, C. L. 1913.")
    got = [c.normalized for c in scan_text(text, resolve=False)]
    for want in ("N.D. Const. § 173", "N.D.R.C. 1943 § 11-1002", "N.D.C.C. § 28-32-19",
                 "1947 N.D. Sess. Laws ch. 176", "N.D.C.L. 1913 § 5841"):
        assert want in got, (want, got)


@pytest.mark.parametrize("text, expected", [
    ("under Chapter 9–09, NDRC 1943. Plaintiff", ["N.D.R.C. 1943 ch. 9-09"]),
    ("Chapter 40–45, N.D.R.C. 1943", ["N.D.R.C. 1943 ch. 40-45"]),
    ("Chapter 26–23 NDRC 1943, being the State Bonding Fund Act", ["N.D.R.C. 1943 ch. 26-23"]),
    ("set forth in Chapter 40–05 of the NDRC 1943. It had", ["N.D.R.C. 1943 ch. 40-05"]),
    ("injunctions generally, Chap. 32–06, NDRC 1943. It is", ["N.D.R.C. 1943 ch. 32-06"]),
    ("Act (chapter 28–32, R.C.N.D.1943, as amended by", ["N.D.R.C. 1943 ch. 28-32"]),
    ("Chapters 24–01 and 24–07, NDRC 1943 as amended", ["N.D.R.C. 1943 ch. 24-01", "N.D.R.C. 1943 ch. 24-07"]),
    ("under Chapter 40—49, Revised Code of 1943. Neither", ["N.D.R.C. 1943 ch. 40-49"]),
    ("§ 1321a1, NDRC 1943, Chapter 15–51. The act", ["N.D.R.C. 1943 ch. 15-51"]),
])
def test_chapters_of_the_1943_code(text, expected):
    cs = M.find_all(text)
    assert [c.normalized for c in cs] == expected
    assert all("section" not in c.components and c.components["chapter"] for c in cs)


def test_chapter_and_section_side_by_side():
    assert norms("Chapter 32–15, NDRC 1943, and Section 32–1501, NDRC 1943.") == [
        "N.D.R.C. 1943 ch. 32-15", "N.D.R.C. 1943 § 32-1501"]
    cs = M.find_all("provisions of Chapter 24-01, NDRC 1953 Supp., any party")
    assert [(c.normalized, c.components["supplement"]) for c in cs] == [("N.D.R.C. 1943 ch. 24-01", "1953")]
