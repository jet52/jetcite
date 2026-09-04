"""Tests for North Dakota-specific citation patterns."""

import pytest

from jetcite.models import CitationType
from jetcite.patterns.states.nd import NDMatcher


def test_ndcc_section():
    m = NDMatcher()
    results = m.find_all("N.D.C.C. § 12.1-32-01")
    assert len(results) == 1
    assert results[0].normalized == "N.D.C.C. § 12.1-32-01"
    assert "ndlegis.gov" in results[0].sources[0].url
    assert "nameddest=12p1-32-01" in results[0].sources[0].url


def test_ndcc_no_periods():
    m = NDMatcher()
    results = m.find_all("NDCC § 1-02-13 ")
    assert len(results) == 1
    assert results[0].normalized == "N.D.C.C. § 1-02-13"


def test_ndcc_section_word():
    m = NDMatcher()
    results = m.find_all("section 14-02-05, N.D.C.C.")
    assert len(results) >= 1


def test_ndcc_chapter():
    m = NDMatcher()
    results = m.find_all("NDCC ch. 14-02")
    assert len(results) == 1
    assert results[0].normalized == "N.D.C.C. ch. 14-02"


def test_ndcc_decimal_title():
    m = NDMatcher()
    results = m.find_all("N.D.C.C. § 12.1-32-01 ")
    assert len(results) == 1
    c = results[0]
    assert c.components["title"] == "12"
    assert c.components["title_dec"] == "1"


def test_ndac_section():
    m = NDMatcher()
    results = m.find_all("N.D.A.C. § 43-02-05-01")
    assert len(results) == 1
    assert results[0].normalized == "N.D.A.C. § 43-02-05-01"
    assert "ndlegis.gov" in results[0].sources[0].url


def test_ndac_chapter():
    m = NDMatcher()
    results = m.find_all("N.D.A.C. ch. 43-02-05")
    assert len(results) == 1
    assert results[0].normalized == "N.D.A.C. ch. 43-02-05"


def test_ndac_prose_section_of_admin_code():
    # Prose form must classify as NDAC (regulation), not NDCC (statute).
    # Regression: previously misparsed as "N.D.C.C. § 75-02-04.1".
    m = NDMatcher()
    results = m.find_all(
        "Section 75-02-04.1-07(7) of the North Dakota Administrative Code.")
    ndac = [r for r in results if r.cite_type == CitationType.REGULATION]
    assert len(ndac) == 1
    c = ndac[0]
    assert c.normalized == "N.D.A.C. § 75-02-04.1-07"
    assert c.components == {
        "part1": "75", "part2": "02", "part3": "04.1", "part4": "07"}
    assert c.pinpoint == "(7)"
    assert "acdata/pdf/75-02-04.1.pdf" in c.sources[0].url
    # The truncated NDCC match must not survive deduplication.
    assert not any(r.normalized == "N.D.C.C. § 75-02-04.1" for r in results)


def test_ndac_bare_four_group_section():
    # A bare four-group "Section" cite is structurally NDAC even without the
    # "Administrative Code" cue (NDCC is always three groups).
    m = NDMatcher()
    results = m.find_all("Section 75-02-04.1-07")
    ndac = [r for r in results if r.cite_type == CitationType.REGULATION]
    assert len(ndac) == 1
    assert ndac[0].normalized == "N.D.A.C. § 75-02-04.1-07"
    assert not any(r.cite_type == CitationType.STATUTE for r in results)


def test_ndac_reverse_section():
    # Reverse form (number then N.D.A.C.) stays classified as NDAC.
    m = NDMatcher()
    results = m.find_all("section 75-02-04.1-07, N.D.A.C.")
    ndac = [r for r in results if r.cite_type == CitationType.REGULATION]
    assert len(ndac) == 1
    assert ndac[0].normalized == "N.D.A.C. § 75-02-04.1-07"


def test_ndac_standard_section_with_subsection():
    # Existing N.D.A.C.-prefixed form is unchanged.
    m = NDMatcher()
    results = m.find_all("N.D.A.C. § 75-02-04.1-07(7)")
    ndac = [r for r in results if r.cite_type == CitationType.REGULATION]
    assert len(ndac) == 1
    assert ndac[0].normalized == "N.D.A.C. § 75-02-04.1-07"


def test_ndcc_three_group_section_unchanged():
    # A three-group "Section" cite with no Admin-Code cue stays NDCC.
    m = NDMatcher()
    results = m.find_all("Section 14-05-24.1")
    statute = [r for r in results if r.cite_type == CitationType.STATUTE]
    assert len(statute) == 1
    assert statute[0].normalized == "N.D.C.C. § 14-05-24.1"
    assert not any(r.cite_type == CitationType.REGULATION for r in results)


def test_ndcc_prose_century_code_unchanged():
    # Prose NDCC with the Century Code cue stays NDCC.
    m = NDMatcher()
    results = m.find_all(
        "Section 14-09-06.2 of the North Dakota Century Code")
    statute = [r for r in results if r.cite_type == CitationType.STATUTE]
    assert len(statute) == 1
    assert statute[0].normalized == "N.D.C.C. § 14-09-06.2"


def test_ndcc_section_wrapped_whitespace():
    # A section number the court's PDF wraps across a line (rendered as a stray
    # space or newline) must still parse as one cite. The space can fall before
    # any hyphen, including the last group. (Regression: 2026-06-20.)
    m = NDMatcher()
    for text in (
        "agency decision under N.D.C.C. §§ 28-32- 46, 28-32-49.",  # space before last group
        "under N.D.C.C. § 12.1-16-\n01, knowingly",                # newline wrap
        "guidelines amount. See N.D.C.C. § 14-09-\n\n00.1 The",    # double-newline wrap
        "pursuant to NDCC § 41 -09-07(1).",                         # space after first group
    ):
        results = m.find_all(text)
        statute = [r for r in results if r.cite_type == CitationType.STATUTE]
        assert statute, f"no statute cite parsed from {text!r}"
        # normalized must be the de-spaced section number
        assert " " not in statute[0].normalized.split("§")[-1].strip().replace(
            "§", ""), statute[0].normalized


def test_ndac_section_wrapped_whitespace():
    m = NDMatcher()
    results = m.find_all("had no control under N.D.A.C. § 75-02-\n04.1-09(2)(j)")
    ndac = [r for r in results if r.cite_type == CitationType.REGULATION]
    assert len(ndac) == 1
    assert ndac[0].normalized == "N.D.A.C. § 75-02-04.1-09"


def test_ndcc_comma_separated_numbers_not_a_section():
    # A dash is now required between groups, so comma-separated numbers after an
    # NDCC cue must NOT be misread as a single section number.
    m = NDMatcher()
    results = m.find_all("N.D.C.C. §§ 12, 34, 56 are unrelated provisions")
    assert not any(
        r.normalized == "N.D.C.C. § 12-34-56" for r in results)


def test_nd_const():
    m = NDMatcher()
    results = m.find_all("N.D. Const. art. I, § 20")
    assert len(results) == 1
    assert results[0].normalized == "N.D. Const. art. I, § 20"
    assert "ndconst.org" in results[0].sources[0].url


def test_nd_const_long():
    m = NDMatcher()
    results = m.find_all("Article VI, section 2 of the North Dakota Constitution")
    assert len(results) == 1
    assert results[0].normalized == "N.D. Const. art. VI, § 2"


def test_nd_const_old_of_the():
    m = NDMatcher()
    for text in (
        "Section 121 of the Constitution",
        "section 121 of the North Dakota Constitution",
        "section 121 of the state Constitution",
        "section 121 of our Constitution",
        "Section 121 of the Constitution of North Dakota",
        "Section 121 of the Constitution of the State of North Dakota",
        "§ 121, of the Constitution",
    ):
        results = m.find_all(text)
        assert len(results) == 1, text
        assert results[0].normalized == "N.D. Const. § 121", text
        assert results[0].components["numbering"] == "1889"
        assert results[0].sources[0].url == "https://ndconst.org/artii/sec1/", text


def test_n_dak_const_old_continuous():
    """`N. Dak.` / `N.Dak.` Const. continuous-section form (1889 numbering)."""
    m = NDMatcher()
    for text in (
        "N. Dak. Const. § 121",
        "N.Dak. Const. § 121",
        "N. Dak.Const. § 121",
        "Section 121, N. Dak. Const.",
    ):
        results = m.find_all(text)
        assert len(results) == 1, text
        assert results[0].normalized == "N.D. Const. § 121", text


def test_n_dak_const_article_form():
    """Modern article/section form with N. Dak. abbreviation."""
    m = NDMatcher()
    results = m.find_all("N. Dak. Const. art. I, § 20")
    assert len(results) == 1
    assert results[0].normalized == "N.D. Const. art. I, § 20"


def test_n_dak_not_bare_dakota_prose():
    """Do not over-match bare 'Dak.' or unadorned 'North Dakota' prose."""
    m = NDMatcher()
    assert m.find_all("the Dak. prairie was dry") == []
    assert m.find_all("North Dakota is a state") == []


def test_nd_const_old_lead_and_trail_comma():
    m = NDMatcher()
    for text in (
        "N.D. Const. § 121",
        "N.D.Const. § 121",
        "Constitution, § 121",
        "North Dakota Constitution, section 121",
        "Section 121, N.D. Const.",
        "Section 121, North Dakota Constitution",
        "section 121, Const.",
    ):
        results = m.find_all(text)
        assert len(results) == 1, text
        assert results[0].normalized == "N.D. Const. § 121", text


def test_nd_const_old_enumeration():
    m = NDMatcher()
    results = m.find_all("under Sections 185 and 186 of the Constitution")
    assert sorted(r.normalized for r in results) == [
        "N.D. Const. § 185", "N.D. Const. § 186"]
    assert results[0].sources[0].url == "https://ndconst.org/artx/sec18/"
    assert results[1].sources[0].url == "https://ndconst.org/artx/sec12/"

    results = m.find_all("sections 179, 180, and 181 of the Constitution")
    assert sorted(r.normalized for r in results) == [
        "N.D. Const. § 179", "N.D. Const. § 180", "N.D. Const. § 181"]


def test_nd_const_old_unmapped_has_no_source():
    # Old § 25 was superseded (no clean modern location in the 1981
    # crosswalk): the cite still parses, but carries no URL.
    m = NDMatcher()
    results = m.find_all("Section 25 of the Constitution")
    assert len(results) == 1
    assert results[0].normalized == "N.D. Const. § 25"
    assert results[0].sources == []


def test_nd_const_old_not_confused_with_article_form():
    m = NDMatcher()
    # Article-scoped cites must yield exactly the modern cite, no phantom
    # old-numbering cite from the "section N of the ... Constitution" tail.
    results = m.find_all("Article VI, section 2 of the North Dakota Constitution")
    assert [r.normalized for r in results] == ["N.D. Const. art. VI, § 2"]
    results = m.find_all("Article II, section 1 of the Constitution")
    assert results == []
    results = m.find_all("N.D. Const. art. I, § 20")
    assert [r.normalized for r in results] == ["N.D. Const. art. I, § 20"]


def test_nd_const_old_rejects_federal_and_sister_state():
    m = NDMatcher()
    for text in (
        "section 1 of the Constitution of the United States",
        "section 2 of the United States Constitution",
        "section 2 of the U.S. Constitution",
        "United States Constitution, § 2",
        "section 15 of the Constitution of Montana",
        "section 15 of the Constitution of the state of Montana",
    ):
        assert m.find_all(text) == [], text


def test_nd_const_old_rejects_bare_lead_sister_state():
    m = NDMatcher()
    # "Montana Constitution, § 2" — the bare-"Constitution" lead form must not
    # fire when a capitalized (state-name) word precedes it (2026-07-22 corpus
    # find: State ex rel. Bottomly-era Montana cite parsed as ND § 2).
    assert m.find_all("See Montana Constitution, § 2, art. 8") == []
    assert m.find_all("the South Dakota Constitution, § 2") == []
    # The allowlisted capitalized prefixes still match.
    for text in ("The Constitution, § 61", "our State Constitution, § 61"):
        results = m.find_all(text)
        assert [r.normalized for r in results] == ["N.D. Const. § 61"], text


def test_nd_const_bracket_altered_article_form():
    m = NDMatcher()
    # Quotation-altered "article [I], section 1 of the North Dakota
    # constitution" is a MODERN cite; it must not fall through to an
    # old-numbering § 1 (2026-07-22 corpus find, 2023/2025 opinions).
    results = m.find_all(
        "a liberty interest in article [I], section 1 of the North Dakota constitution")
    assert [r.normalized for r in results] == ["N.D. Const. art. I, § 1"]
    assert all(r.components.get("numbering") != "1889" for r in results)


def test_nd_const_old_rejects_modern_context_shapes():
    m = NDMatcher()
    # 2026-07-22 corpus finds: post-1981 opinions writing MODERN cites in
    # shapes that leaked through to the old-numbering patterns.
    for text in (
        # "subsection 21" must not match as "section 21"
        "Article IV, Section 43, subsection 21, of the North Dakota Constitution",
        # statute number in a string cite after N.D. Const.
        "under Art. V, Sec. 12, N.D. Const., Section 16.1-11-08, N.D.C.C.",
        # article named AFTER the Const marker (tail-first modern cite)
        "Sections 1 and 10, N.D. Const. art. III, provide that",
        "Section 25 of the North Dakota Constitution, Article I",
        # enumeration continuing an article-scoped cite
        "with Article I, § 3 and § 4 of the North Dakota Constitution",
        # star-page marker between article and section
        "became Article VI, [*348] Section 3 of the North Dakota Constitution.",
        # section scoped to an article named earlier in the sentence
        "Article VI, section 3, N.D.Const., section 6, of that same Article",
    ):
        olds = [r for r in m.find_all(text)
                if r.components.get("numbering") == "1889"]
        assert olds == [], (text, olds)
    # statute-shaped numbers after a Constitution marker stay dead
    for text, want in (
        ("Sec. 173, Constitution, Sec. 11-1002, NDRC 1943.",
         ["N.D. Const. § 173"]),
        ("Constitution of the State of North Dakota, Section 54-03-01 "
         "of the North Dakota Century Code", []),
    ):
        olds = [r.normalized for r in m.find_all(text)
                if r.components.get("numbering") == "1889"]
        assert olds == want, (text, olds)
    # ...but true-positive neighbors of those guards survive:
    # a new sentence starting "Article" does not poison a preceding old cite
    results = m.find_all(
        "under § 176 of the Constitution. Article VI provides otherwise")
    assert [r.normalized for r in results] == ["N.D. Const. § 176"]
    # a semicolon ends a string cite — the ND cite after a federal one lives
    results = m.find_all("U. S. Const. art. 1, § 10; N. D. Const. § 16.")
    assert "N.D. Const. § 16" in [r.normalized for r in results]
    # ...as does the older comma-separated string-cite style: an ND-marked
    # lead cite is never scoped by the preceding federal article reference
    results = m.find_all("U.S.Const. art. 1, § 10, N.D.Const. § 16.")
    assert "N.D. Const. § 16" in [r.normalized for r in results]
    # "the new constitution § 5" refers to the replacement document
    olds = [r for r in m.find_all("The new constitution § 5 provides")
            if r.components.get("numbering") == "1889"]
    assert olds == []
    # a section RANGE keeps its start section
    olds = [r.normalized for r in m.find_all(
        "N.Dak. Constitution, Secs. 130, 166–173, 175")
        if r.components.get("numbering") == "1889"]
    assert olds == ["N.D. Const. § 130", "N.D. Const. § 166"]
    # an arabic-numbered AMENDMENT article after "Constitution," is old context
    results = m.find_all(
        "section 202 of the Constitution, article 28 of Amendments thereto.")
    assert [r.normalized for r in results] == ["N.D. Const. § 202"]


def test_nd_const_old_rejects_out_of_range():
    m = NDMatcher()
    assert m.find_all("section 218 of the Constitution") == []
    assert m.find_all("section 300 of the Constitution") == []
    assert m.find_all("Constitution, § 999") == []


def test_nd_rule_civ_p():
    m = NDMatcher()
    results = m.find_all("N.D.R.Civ.P. Rule 56")
    assert len(results) >= 1
    found = [r for r in results if "ndrcivp" in r.components.get("rule_set", "")]
    assert len(found) >= 1
    assert "ndcourts.gov" in found[0].sources[0].url


def test_rule_set_markers_compact_and_spaced():
    from jetcite.patterns.states.nd import rule_set_markers

    hits = rule_set_markers("Under N.D.R.Civ.P. 12 and N. D. R. Civ. P. 56")
    assert [h[2] for h in hits] == ["N.D.R.Civ.P.", "N.D.R.Civ.P."]


def test_rule_set_markers_spelled_out():
    from jetcite.patterns.states.nd import rule_set_markers

    hits = rule_set_markers("the Rules of Criminal Procedure govern")
    assert [h[2] for h in hits] == ["N.D.R.Crim.P."]


def test_rule_set_markers_spelled_state_forms():
    """Every ND set carries its "North Dakota ..." form, kept whole by the
    containment dedup — without it the state name is left outside the marker
    and a trailing attribution reaching through it is rejected."""
    from jetcite.patterns.states.nd import rule_set_markers

    for text, canon in (
        ("the North Dakota Rules of Appellate Procedure", "N.D.R.App.P."),
        ("the North Dakota Rules of Criminal Procedure", "N.D.R.Crim.P."),
        ("the North Dakota Rules of Evidence", "N.D.R.Ev."),
        ("the North Dakota Rule of Evidence", "N.D.R.Ev."),
        ("the North Dakota Rules of Court", "N.D.R.Ct."),
        ("the North Dakota Rules of Juvenile Procedure", "N.D.R.Juv.P."),
        ("the North Dakota Rules of Professional Conduct", "N.D.R. Prof. Conduct"),
        ("the North Dakota Code of Judicial Conduct", "N.D. Code Jud. Conduct"),
    ):
        hits = rule_set_markers(text)
        assert [h[2] for h in hits] == [canon], text
        assert text[hits[0][0]:hits[0][1]].startswith("North Dakota"), text


def test_rule_set_markers_six_added_sets():
    """The six sets that parsed compact but had no spelled marker (TODO,
    "six ND rule sets have no spelled-out marker"): the state-prefixed name
    must be one whole marker so a trailing attribution can reach it."""
    from jetcite.patterns.states.nd import rule_set_markers

    for text, canon in (
        ("the North Dakota Supreme Court Administrative Rules",
         "N.D. Sup. Ct. Admin. R."),
        ("the North Dakota Supreme Court Administrative Orders",
         "N.D. Sup. Ct. Admin. Order"),
        ("the North Dakota Rules for Lawyer Discipline",
         "N.D.R. Lawyer Discipl."),
        ("the North Dakota Admission to Practice Rules",
         "N.D. Admission to Practice R."),
        ("the North Dakota Rules for Continuing Legal Education",
         "N.D.R. Continuing Legal Ed."),
        ("the North Dakota Rules of the Judicial Conduct Commission",
         "N.D.R. Jud. Conduct Commission"),
    ):
        hits = rule_set_markers(text)
        assert [h[2] for h in hits] == [canon], text
        assert text[hits[0][0]:hits[0][1]].startswith("North Dakota"), text


def test_trailing_attribution_reaches_the_six_added_sets():
    """The certificate-of-compliance shape for the added vocabularies."""
    from jetcite import scan_text

    for text, parent in (
        ("See Rule 5 of the North Dakota Rules for Lawyer Discipline.",
         "N.D.R. Lawyer Discipl. 5"),
        ("Under Rule 11 of the North Dakota Supreme Court Administrative "
         "Rules.", "N.D. Sup. Ct. Admin. R. 11"),
        ("Rule 3 of the North Dakota Admission to Practice Rules governs.",
         "N.D. Admission to Practice R. 3"),
        ("Rule 4 of the North Dakota Rules for Continuing Legal Education "
         "applies.", "N.D.R. Continuing Legal Ed. 4"),
        ("Rule 2.1 of the North Dakota Rules of the Judicial Conduct "
         "Commission controls.", "N.D.R. Jud. Conduct Commission 2.1"),
    ):
        cites = scan_text(text, include_pin_cites=True)
        assert [c.parent_normalized for c in cites] == [parent], text


def test_spelled_leading_full_cites():
    """"North Dakota Rule of Evidence 201 governs" — the leading spelled
    form no compact matcher or trailing rung could reach (TODO,
    "spelled-out leading rule form is unmatched")."""
    from jetcite import scan_text

    for text, want in (
        ("North Dakota Rule of Evidence 201 governs judicial notice.",
         "N.D.R.Ev. 201"),
        ("the North Dakota Rules of Civil Procedure 56 standard.",
         "N.D.R.Civ.P. 56"),
        ("North Dakota Rule of Appellate Procedure 32 sets the limits.",
         "N.D.R.App.P. 32"),
        ("the North Dakota Code of Judicial Conduct Rule 2.11 requires "
         "recusal.", "N.D. Code Jud. Conduct 2.11"),
        ("North Dakota Supreme Court Administrative Rule 11 applies.",
         "N.D. Sup. Ct. Admin. R. 11"),
        ("North Dakota Rule for Lawyer Discipline 5 sets the procedure.",
         "N.D.R. Lawyer Discipl. 5"),
    ):
        assert want in [c.normalized for c in scan_text(text)], text
    # the North Dakota prefix is required (federal ambiguity), prose and
    # year-like numbers must not match
    for text in (
        "Rules of Evidence 201 without the state name.",
        "the rules of court are strict here.",
        "the North Dakota Rules of Court 2020 edition was in force.",
    ):
        assert scan_text(text) == [], text


def test_rule_set_markers_containment_dedup():
    """'Rules of Civil Procedure' inside 'Federal Rules of Civil Procedure'
    must not produce a second, ND-attributed marker."""
    from jetcite.patterns.states.nd import rule_set_markers

    hits = rule_set_markers("the Federal Rules of Civil Procedure apply")
    assert [h[2] for h in hits] == ["Fed. R. Civ. P."]


def test_nd_rule_trailing_form_rejects_semicolon_gap():
    """A semicolon is a string-cite boundary: "2024 ND 4; N.D.R.Civ.P. 60(b)"
    must not splice the neutral cite's "4" into a phantom rule cite."""
    m = NDMatcher()
    results = m.find_all("See State v. Gonzalez, 2024 ND 4; N.D.R.Civ.P. 60(b).")
    rules = [r for r in results if "rule_set" in r.components]
    assert [r.normalized for r in rules] == ["N.D.R.Civ.P. 60"]


@pytest.mark.parametrize("text,expected", [
    ("[¶12] N.D.R.Civ.P. 55(a)(3) states:", "N.D.R.Civ.P. 55"),
    ("[¶ 7] N.D.R.App.P. 4(a)(1) governs.", "N.D.R.App.P. 4"),
    ("[¶3] N.D.R.Crim.P. 11 applies.", "N.D.R.Crim.P. 11"),
    ("[¶404] N.D.R.Ev. 801 defines hearsay.", "N.D.R.Ev. 801"),
    ("[¶35] N.D. Sup. Ct. Admin. R. 41 applies.", "N.D. Sup. Ct. Admin. R. 41"),
    ("[¶5] N.D.R. Prof. Conduct 1.7 applies.", "N.D.R. Prof. Conduct 1.7"),
])
def test_nd_rule_trailing_form_rejects_paragraph_marker_gap(text, expected):
    """A "]" closes a paragraph marker, so "[¶12] N.D.R.Civ.P. 55(a)(3)" must
    not splice the marker's "12" into a phantom "N.D.R.Civ.P. 12" — the same
    boundary rule the semicolon test covers. Where the trailing and leading
    rule numbers share an arity (N.D.R.Ev., N.D. Sup. Ct. Admin. R.) the
    phantom overlapped and replaced the real cite instead of merely doubling
    it, so the real rule went missing entirely."""
    m = NDMatcher()
    rules = [r for r in m.find_all(text) if "rule_set" in r.components]
    assert [r.normalized for r in rules] == [expected]


@pytest.mark.parametrize("text,expected", [
    # 3-part number, 2-part pattern: "3.1" is the tail of "8.3.1"
    ("Rule 8.3.1, N.D.R.Ct., applies.", ["N.D.R.Ct. 8.3.1"]),
    # 2-part number, 1-part pattern: "3" is the tail of "8.3"
    ("Rule 8.3, N.D. Sup. Ct. Admin. R., applies.",
     ["N.D. Sup. Ct. Admin. R. 8.3"]),
    # Unaffected trailing forms
    ("Rule 11.10, N.D.R.Ct., applies.", ["N.D.R.Ct. 11.10"]),
    ("Rule 3.2, N.D.R.Ct., applies.", ["N.D.R.Ct. 3.2"]),
    ("Rule 35, N.D. Sup. Ct. Admin. R., applies.",
     ["N.D. Sup. Ct. Admin. R. 35"]),
    ("Rule 60(b), N.D.R.Civ.P., governs.", ["N.D.R.Civ.P. 60"]),
    ("Rule 404(b), N.D.R.Ev., bars it.", ["N.D.R.Ev. 404"]),
    ("Rule 1.7, N.D.R. Prof. Conduct, applies.",
     ["N.D.R. Prof. Conduct 1.7"]),
    # Leading forms were never vulnerable — the same-position dedup pass
    # already keeps the longer match — but pin them so they stay that way.
    ("N.D.R.Ct. 8.3.1 applies.", ["N.D.R.Ct. 8.3.1"]),
    ("N.D. Sup. Ct. Admin. R. 8.3 applies.",
     ["N.D. Sup. Ct. Admin. R. 8.3"]),
])
def test_nd_rule_trailing_form_rejects_tail_of_longer_number(text, expected):
    """A lower-arity trailing pattern must not match the tail of a
    higher-arity rule number. "Rule 8.3.1, N.D.R.Ct." yielded a spurious
    "N.D.R.Ct. 3.1" alongside the real cite, and "Rule 8.3, N.D. Sup. Ct.
    Admin. R." a spurious "R. 3" — neither caught by find_all's dedup, since
    the tail starts later and normalizes differently."""
    m = NDMatcher()
    rules = [r for r in m.find_all(text) if "rule_set" in r.components]
    assert [r.normalized for r in rules] == expected


def test_nd_rule_ev():
    m = NDMatcher()
    results = m.find_all("N.D.R.Ev. 803")
    assert len(results) == 1
    assert "ndrev" in results[0].components["rule_set"]


def test_nd_rule_crim_p():
    m = NDMatcher()
    results = m.find_all("N.D.R.Crim.P. 29")
    assert len(results) >= 1


def test_nd_rule_ct_3part():
    m = NDMatcher()
    results = m.find_all("N.D.R.Ct. 8.3.1")
    assert len(results) == 1
    assert "ndrct" in results[0].components["rule_set"]


def test_nd_admin_rule():
    m = NDMatcher()
    results = m.find_all("N.D. Sup. Ct. Admin. R. 1.2")
    assert len(results) == 1
    assert "ndsupctadminr" in results[0].components["rule_set"]


def test_nd_prof_conduct():
    m = NDMatcher()
    results = m.find_all("N.D.R. Prof. Conduct 1.1")
    assert len(results) == 1
    assert "ndrprofconduct" in results[0].components["rule_set"]


def test_local_rule():
    m = NDMatcher()
    results = m.find_all("Local Rule 100-1")
    assert len(results) == 1
    assert "local" in results[0].components["rule_set"]


# ---------------------------------------------------------------------------
# N.D. Sup. Ct. Admin. Order — and the agency-order decoys it must refuse
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    # the set names itself
    ("N.D. Sup.Ct. Admin. Order 9 provides, in part:",
     "N.D. Sup. Ct. Admin. Order 9"),
    ("timely under N.D.R.App.P. 4(a) and N.D. Sup.Ct. Admin. Order 20.",
     "N.D. Sup. Ct. Admin. Order 20"),
    ("See N.D. Sup. Ct. Admin. Order 25 (first adopted March 16, 2020).",
     "N.D. Sup. Ct. Admin. Order 25"),
    ("Sup. Ct. Admin. Order 16 governs.", "N.D. Sup. Ct. Admin. Order 16"),
    # the court owns it
    ("Consistent with this Court's Administrative Order 25 suspending trials",
     "N.D. Sup. Ct. Admin. Order 25"),
    ("Administrative Order No. 1 of this Court, dated October 30, 1974",
     "N.D. Sup. Ct. Admin. Order 1"),
])
def test_nd_admin_order(text, expected):
    m = NDMatcher()
    got = [c.normalized for c in m.find_all(text)
           if "Admin. Order" in c.normalized]
    assert got == [expected]


@pytest.mark.parametrize("text", [
    # agency orders: hyphen-suffixed docket numbers are never this set
    "the State Engineer's Administrative Order 10-1 requiring Peterson",
    "Administrative Order 2-1979 designated Judge A. C. Bakken",
    # ordinary prose about an agency's order
    "an administrative order of revocation of driver's license was made",
    "affirmed an administrative order entered after hearing on July 5, 1973",
    # bare short form with no cue: left to the opinion's own full cite
    "trial continuances caused by Administrative Order 25 do not weigh",
])
def test_nd_admin_order_refuses_agency_orders(text):
    m = NDMatcher()
    assert [c.normalized for c in m.find_all(text)
            if "Admin. Order" in c.normalized] == []


def test_nd_admin_order_distinct_from_admin_rule():
    m = NDMatcher()
    got = [c.normalized for c in m.find_all(
        "N.D. Sup. Ct. Admin. R. 22 and N.D. Sup. Ct. Admin. Order 25")]
    assert "N.D. Sup. Ct. Admin. R. 22" in got
    assert "N.D. Sup. Ct. Admin. Order 25" in got


# ---------------------------------------------------------------------------
# N.D.R. Proc. R. — the court writes it with a section sign and a decimal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    # a decimal here is a SUBSECTION pinpoint, normalized to its section
    ('Under N.D.R.Proc.R. § 3.1, "Any person interested', "N.D.R. Proc. R. 3"),
    ("can petition under N.D.R.Proc.R. § 3.1 to request", "N.D.R. Proc. R. 3"),
    ("N.D.R. Proc. R. 10 does not act as a stay", "N.D.R. Proc. R. 10"),
])
def test_nd_proc_r(text, expected):
    m = NDMatcher()
    got = [c.normalized for c in m.find_all(text) if "Proc. R." in c.normalized]
    assert got == [expected]


def test_nd_proc_r_bare_set_reference_is_not_a_cite():
    m = NDMatcher()
    assert [c.normalized for c in m.find_all(
        "See generally N.D.R.Proc.R. Judge Schmidt did not err")
        if "Proc. R." in c.normalized] == []


# ---------------------------------------------------------------------------
# the two sets ND opinions do not cite by number — normalized forms aligned
# with the rules corpus so a future cite resolves
# ---------------------------------------------------------------------------

def test_nd_local_ct_pr_normalizes_to_corpus_form():
    m = NDMatcher()
    got = [c.normalized for c in m.find_all("N.D.R. Local Ct. Pr. 3")]
    assert got == ["N.D.R. Local Ct. Pr. 3"]


def test_nd_student_practice_roman_becomes_arabic():
    # headings print roman numerals; the corpus cites arabic
    m = NDMatcher()
    got = [c.normalized for c in m.find_all(
        "Limited Practice of Law by Law Students R. VII")]
    assert got == ["Ltd. Practice of Law by Law Students R. 7"]


def test_nd_student_practice_appearance_line_is_not_a_cite():
    # all 118 corpus mentions are counsel-appearance lines; the street number
    # that follows must never be read as a rule number
    m = NDMatcher()
    assert [c.normalized for c in m.find_all(
        "under the Rule on Limited Practice of Law by Law Students, "
        "124 South Fourth Street, Bismarck")
        if "Law Students" in c.normalized] == []


def test_nd_proc_r_decimal_is_a_subsection_pinpoint():
    """Proc. R. and Local Ct. Pr. number sections with integers and
    subsections with decimals, so '§ 3.1' must resolve to section 3 (which
    the rules corpus carries) with the pinpoint preserved."""
    m = NDMatcher()
    cite = [c for c in m.find_all('N.D.R.Proc.R. § 3.1 permits a petition')
            if "Proc. R." in c.normalized][0]
    assert cite.normalized == "N.D.R. Proc. R. 3"
    assert cite.components["pinpoint"] == "3.1"
