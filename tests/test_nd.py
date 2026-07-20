"""Tests for North Dakota-specific citation patterns."""

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
