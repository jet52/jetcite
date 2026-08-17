"""Tests for enumerated citation lists and the plural-marker anchors.

Three things are under test here, and they are related but distinct:

* **Plural-marker anchors.** ``§§``, ``Sections``, ``Secs.``, ``chs.``, and
  ``Rules`` are the ordinary spellings when more than one provision is cited.
  Before this work each of them *rejected the anchor outright* in at least one
  family, so the citation was not merely truncated — it disappeared.
* **The NDCC comma-swallow.** The Century Code attribution used to be consumed
  rather than looked ahead at, so a comma-separated pair of fully-spelled
  cites lost its second member.
* **Enumeration expansion** proper — recovering the tail members.

Every string marked *(corpus)* is taken verbatim from the North Dakota
opinions corpus, so the suite is anchored on citation forms the court actually
writes rather than on forms that seemed plausible while writing the parser.

The false-positive tests matter more than the true-positive ones. Expansion
invents citations that were never matched by a pattern, which is exactly the
operation most likely to manufacture a plausible-looking cite out of a page
number, a reporter volume, or the first member of the *next* authority.
"""

import pytest

from jetcite.models import CitationType
from jetcite.scanner import scan_text


def norms(text: str) -> list[str]:
    """Normalized citations, deduplicated by the scanner, in document order."""
    return [c.normalized for c in scan_text(text, resolve=False)]


def cites(text: str) -> list:
    return list(scan_text(text, resolve=False))


def enumerated(text: str) -> list[str]:
    """Only the citations recovered by list expansion."""
    return [
        c.normalized
        for c in scan_text(text, resolve=False)
        if c.components.get("enumerated")
    ]


# ---------------------------------------------------------------------------
# Regression: plural markers must not destroy the anchor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Section 28-32-19, N.D.C.C.", "N.D.C.C. § 28-32-19"),
        ("Sections 28-32-19, N.D.C.C.", "N.D.C.C. § 28-32-19"),
        ("Sec. 28-32-19, N.D.C.C.", "N.D.C.C. § 28-32-19"),
        ("Secs. 28-32-19, N.D.C.C.", "N.D.C.C. § 28-32-19"),
        ("N.D.C.C. § 28-32-19", "N.D.C.C. § 28-32-19"),
        ("N.D.C.C. §§ 28-32-19", "N.D.C.C. § 28-32-19"),
    ],
)
def test_plural_section_marker_keeps_anchor(text, expected):
    assert expected in norms(text)


def test_plural_chapter_marker_keeps_anchor():
    assert "N.D.C.C. ch. 27-20" in norms("N.D.C.C. ch. 27-20")
    assert "N.D.C.C. ch. 27-20" in norms("N.D.C.C. chs. 27-20")


def test_plural_constitution_marker_keeps_anchor():
    assert "N.D. Const. art. VI, § 2" in norms("N.D. Const. art. VI, § 2")
    assert "N.D. Const. art. VI, § 2" in norms("N.D. Const. art. VI, §§ 2")


def test_plural_rule_marker_keeps_anchor():
    assert "N.D.R.Civ.P. 52" in norms("N.D.R.Civ.P. Rule 52")
    assert "N.D.R.Civ.P. 52" in norms("N.D.R.Civ.P. Rules 52")


# ---------------------------------------------------------------------------
# Regression: a consumed attribution used to swallow the next citation
# ---------------------------------------------------------------------------


def test_two_full_ndcc_cites_separated_by_comma():
    """The trailing "N.D.C.C." belongs to the SECOND cite, not the first."""
    result = norms("N.D.C.C. § 11-11-39, N.D.C.C. § 11-11-43")
    assert result == ["N.D.C.C. § 11-11-39", "N.D.C.C. § 11-11-43"]


def test_three_full_ndcc_cites_separated_by_commas():
    result = norms(
        "N.D.C.C. § 11-11-39, N.D.C.C. § 11-11-43, N.D.C.C. § 28-34-01"
    )
    assert result == [
        "N.D.C.C. § 11-11-39",
        "N.D.C.C. § 11-11-43",
        "N.D.C.C. § 28-34-01",
    ]


@pytest.mark.parametrize("joiner", [" and ", ". ", "; ", " (2023) and "])
def test_two_full_ndcc_cites_other_joiners(joiner):
    text = f"N.D.C.C. § 11-11-39{joiner}N.D.C.C. § 28-34-01"
    assert norms(text) == ["N.D.C.C. § 11-11-39", "N.D.C.C. § 28-34-01"]


# ---------------------------------------------------------------------------
# Expansion — N.D.C.C. sections
# ---------------------------------------------------------------------------


def test_ndcc_list_comma_and():
    """The citation from the bench memo that started this work."""
    assert norms("N.D.C.C. §§ 11-11-39, 11-11-43, and 28-34-01") == [
        "N.D.C.C. § 11-11-39",
        "N.D.C.C. § 11-11-43",
        "N.D.C.C. § 28-34-01",
    ]


def test_ndcc_list_members_may_span_titles():
    """Arity, not a shared title, is the congruence test.

    28-34-01 sits in a different title from 11-11-39; requiring a matching
    title would silently drop the last member of the most common kind of list.
    """
    result = norms("N.D.C.C. §§ 11-11-39, 11-11-43, and 28-34-01")
    assert "N.D.C.C. § 28-34-01" in result


def test_ndcc_list_and_only():
    # (corpus) the single most frequent NDCC list form
    assert norms("N.D.C.C. §§ 28-27-01 and 28-27-02.") == [
        "N.D.C.C. § 28-27-01",
        "N.D.C.C. § 28-27-02",
    ]


def test_ndcc_list_trailing_attribution():
    # (corpus) "Sections 28-32-19 and 28-32-21, N.D.C.C."
    assert norms("Sections 28-32-19 and 28-32-21, N.D.C.C.") == [
        "N.D.C.C. § 28-32-19",
        "N.D.C.C. § 28-32-21",
    ]


def test_ndcc_list_semicolon_separated():
    # (corpus) "N.D.C.C. §§ 9-07-02; 9-07-04; 9-07-06; 9-07-09; and 9-07-12"
    assert norms("See N.D.C.C. §§ 9-07-02; 9-07-04; 9-07-06; 9-07-09; and 9-07-12.") == [
        "N.D.C.C. § 9-07-02",
        "N.D.C.C. § 9-07-04",
        "N.D.C.C. § 9-07-06",
        "N.D.C.C. § 9-07-09",
        "N.D.C.C. § 9-07-12",
    ]


def test_ndcc_list_or_separator():
    # (corpus) "N.D.C.C. §§ 28-27-02 or 29-28-06"
    assert norms("under either N.D.C.C. §§ 28-27-02 or 29-28-06.") == [
        "N.D.C.C. § 28-27-02",
        "N.D.C.C. § 29-28-06",
    ]


def test_ndcc_list_and_or_separator():
    # (corpus) "Sections 12.1-09-01, 12.1-08-05, and/or 19-03.1-23"
    result = norms("Sections 12.1-09-01, 12.1-08-05, and/or 19-03.1-23, N.D.C.C.")
    assert result == [
        "N.D.C.C. § 12.1-09-01",
        "N.D.C.C. § 12.1-08-05",
        "N.D.C.C. § 19-03.1-23",
    ]


def test_ndcc_list_ampersand_separator():
    # (corpus) "§§ 28-32-19 & 28-32-21"
    assert norms("N.D.C.C. §§ 28-32-19 & 28-32-21") == [
        "N.D.C.C. § 28-32-19",
        "N.D.C.C. § 28-32-21",
    ]


def test_ndcc_list_en_dash_numbers():
    # (corpus) opinions print section numbers with en dashes
    assert norms("Sections 32–19–04 and 32–19–06, N.D.C.C.") == [
        "N.D.C.C. § 32-19-04",
        "N.D.C.C. § 32-19-06",
    ]


def test_ndcc_list_em_dash_numbers():
    # (corpus) "Sections 26—03—26, 26—03—27, 26—03—29, and 26—03—30, N.D.C.C."
    assert norms("Sections 26—03—26, 26—03—27, 26—03—29, and 26—03—30, N.D.C.C.") == [
        "N.D.C.C. § 26-03-26",
        "N.D.C.C. § 26-03-27",
        "N.D.C.C. § 26-03-29",
        "N.D.C.C. § 26-03-30",
    ]


def test_ndcc_list_members_with_subdivisions():
    # (corpus) "N.D.C.C. §§ 1-02-07 and 1-02-38(2)"
    assert norms("N.D.C.C. §§ 1-02-07 and 1-02-38(2).") == [
        "N.D.C.C. § 1-02-07",
        "N.D.C.C. § 1-02-38",
    ]


def test_ndcc_list_decimal_titles():
    # (corpus) "§§ 12.1–05–01, 12.1–05–03, and 12.1–05–04, N.D.C.C."
    assert norms("N.D.C.C. §§ 12.1-05-01, 12.1-05-03, and 12.1-05-04.") == [
        "N.D.C.C. § 12.1-05-01",
        "N.D.C.C. § 12.1-05-03",
        "N.D.C.C. § 12.1-05-04",
    ]


# ---------------------------------------------------------------------------
# Expansion — truncated tail members
# ---------------------------------------------------------------------------


def test_truncated_member_inherits_leading_groups():
    # (corpus) "Sections 12.1-23-01, 02, N.D.C.C."
    assert norms("Sections 12.1-23-01, 02, N.D.C.C.") == [
        "N.D.C.C. § 12.1-23-01",
        "N.D.C.C. § 12.1-23-02",
    ]


def test_truncated_member_before_bracketed_parallel():
    # (corpus) "§§ 14-14-07, 08 [UCCJA §§ 7, 8]."
    result = norms("N.D.C.C. §§ 14-14-07, 08 [UCCJA §§ 7, 8].")
    assert result[:2] == ["N.D.C.C. § 14-14-07", "N.D.C.C. § 14-14-08"]


def test_truncated_member_rejected_for_low_arity():
    """A bare number after an arity-1 anchor is not a member.

    Treatise and reporter cites are full of "§§ 590, 618, 639" shapes, and a
    one-group anchor gives the expander nothing to inherit, so truncation is
    confined to the dash-numbered codes.
    """
    assert enumerated("N.D. Const. art. VI, §§ 2, 6") == ["N.D. Const. art. VI, § 6"]


# ---------------------------------------------------------------------------
# Expansion — ranges
# ---------------------------------------------------------------------------


def test_range_through_records_both_endpoints():
    # (corpus) "§§ 28-27-01 through 28-27-02."
    assert norms("N.D.C.C. §§ 28-27-01 through 28-27-02.") == [
        "N.D.C.C. § 28-27-01",
        "N.D.C.C. § 28-27-02",
    ]


def test_range_to_records_both_endpoints():
    # (corpus) "§§ 40-22-18 to 40-22-36."
    assert norms("N.D.C.C. §§ 40-22-18 to 40-22-36.") == [
        "N.D.C.C. § 40-22-18",
        "N.D.C.C. § 40-22-36",
    ]


def test_range_does_not_interpolate_interior():
    """Only the endpoints are emitted.

    The library has no inventory of which sections exist, and with decimal
    section numbers the interior is not enumerable in the first place.
    """
    result = norms("N.D.C.C. §§ 24-02-26 through 24-02-33.")
    assert result == ["N.D.C.C. § 24-02-26", "N.D.C.C. § 24-02-33"]
    assert "N.D.C.C. § 24-02-30" not in result


def test_range_endpoints_are_cross_linked():
    cs = {c.normalized: c for c in cites("N.D.C.C. §§ 28-27-01 through 28-27-02.")}
    assert cs["N.D.C.C. § 28-27-01"].components.get("range_end") == "28-27-02"
    assert cs["N.D.C.C. § 28-27-02"].components.get("range_start") == "28-27-01"


def test_bare_dash_is_not_a_range():
    """A dash between provision numbers is ambiguous and is never a range.

    "55-4401-55-4426" is either two four-group numbers or one eight-group
    number, and in prose a dash is also how page and date spans are written.
    """
    assert enumerated("N.D.C.C. §§ 28-27-01-28-27-02") == []


# ---------------------------------------------------------------------------
# Expansion — chapters, admin code, constitution, rules
# ---------------------------------------------------------------------------


def test_ndcc_chapter_list():
    # (corpus) "N.D.C.C. chs. 27-20.2, 27-20.3, and 27-20.4"
    assert norms("under the Juvenile Court Act, N.D.C.C. chs. 27-20.2, 27-20.3, and 27-20.4,") == [
        "N.D.C.C. ch. 27-20.2",
        "N.D.C.C. ch. 27-20.3",
        "N.D.C.C. ch. 27-20.4",
    ]


def test_ndcc_chapter_list_from_appellants_brief():
    """(corpus form) The list that this appellant's brief cited and jetcite lost."""
    assert norms("N.D.C.C. chs. 57-39.2, 57-39.5, 57-39.6, and 57-40.2") == [
        "N.D.C.C. ch. 57-39.2",
        "N.D.C.C. ch. 57-39.5",
        "N.D.C.C. ch. 57-39.6",
        "N.D.C.C. ch. 57-40.2",
    ]


def test_ndac_list_and():
    # (corpus) "N.D.A.C. §§ 75–02–04.1–01 and 75–02–04.1–02."
    assert norms("N.D.A.C. §§ 75-02-04.1-01 and 75-02-04.1-02.") == [
        "N.D.A.C. § 75-02-04.1-01",
        "N.D.A.C. § 75-02-04.1-02",
    ]


def test_ndac_list_semicolon():
    # (corpus) "N.D.A.C. §§ 59.5–03–03–02(1); 4–07–19–02(1)."
    assert norms("N.D.A.C. §§ 59.5-03-03-02(1); 4-07-19-02(1).") == [
        "N.D.A.C. § 59.5-03-03-02",
        "N.D.A.C. § 4-07-19-02",
    ]


def test_constitution_section_list():
    # (corpus) the most frequent enumerated citation in the ND corpus
    assert norms("This Court has jurisdiction under N.D. Const. art. VI, §§ 2 and 6.") == [
        "N.D. Const. art. VI, § 2",
        "N.D. Const. art. VI, § 6",
    ]


def test_constitution_members_inherit_the_article():
    """The article is stated once and is not part of the enumerable number."""
    cs = {c.normalized: c for c in cites("N.D. Const. art. I, §§ 1 and 23")}
    assert cs["N.D. Const. art. I, § 23"].components["article"] == "I"


def test_rule_list_trailing_marker_expands_backward():
    # (corpus) "Rules 50 and 59, N.D.R.Civ.P., are illustrative"
    assert norms("Rules 50 and 59, N.D.R.Civ.P., are illustrative") == [
        "N.D.R.Civ.P. 50",
        "N.D.R.Civ.P. 59",
    ]


def test_rule_list_trailing_marker_three_members():
    # (corpus) "Rules 10, 28, and 30, N.D.R.App.P."
    assert norms("Rules 10, 28, and 30, N.D.R.App.P., provide") == [
        "N.D.R.App.P. 10",
        "N.D.R.App.P. 28",
        "N.D.R.App.P. 30",
    ]


def test_rule_list_dotted_numbers():
    # (corpus) "North Dakota Rules of Professional Conduct 1.1, 1.3, 1.4 and 1.5"
    result = norms(
        "North Dakota Rules of Professional Conduct 1.1, 1.3, 1.4 and 1.5 require"
    )
    assert "N.D.R. Prof. Conduct 1.3" in result
    assert "N.D.R. Prof. Conduct 1.5" in result


# ---------------------------------------------------------------------------
# Expansion — federal
# ---------------------------------------------------------------------------


def test_usc_list():
    assert norms("42 U.S.C. §§ 1983, 1985, and 1988") == [
        "42 U.S.C. § 1983",
        "42 U.S.C. § 1985",
        "42 U.S.C. § 1988",
    ]


def test_usc_members_inherit_title():
    cs = {c.normalized: c for c in cites("42 U.S.C. §§ 1983, 1988")}
    assert cs["42 U.S.C. § 1988"].components["title"] == "42"


def test_usc_list_with_subdivisions():
    # (corpus) "42 U.S.C. §§ 402(a) and 416(l) (1994)"
    assert norms("See 42 U.S.C. §§ 402(a) and 416(l) (1994).") == [
        "42 U.S.C. § 402(a)",
        "42 U.S.C. § 416",
    ]


def test_usc_range():
    # (corpus) "25 U.S.C. §§ 1901 through 1963"
    assert norms("the Indian Child Welfare Act of 1978 [25 U.S.C. §§ 1901 through 1963]") == [
        "25 U.S.C. § 1901",
        "25 U.S.C. § 1963",
    ]


def test_cfr_list():
    assert norms("29 C.F.R. §§ 1910.1200 and 1910.1201") == [
        "29 C.F.R. § 1910.1200",
        "29 C.F.R. § 1910.1201",
    ]


# ---------------------------------------------------------------------------
# False positives — the list must stop where the authority stops
# ---------------------------------------------------------------------------


def test_list_stops_at_a_new_authority_marker():
    """(corpus) The most common enumerated form in the corpus ends this way.

    "art. VI, §§ 2 and 6, and N.D.C.C. § 28-27-01" — the ", and" after 6 leads
    into a different code, and the constitutional list must not annex it.
    """
    result = norms("N.D. Const. art. VI, §§ 2 and 6, and N.D.C.C. § 28-27-01.")
    assert result == [
        "N.D. Const. art. VI, § 2",
        "N.D. Const. art. VI, § 6",
        "N.D.C.C. § 28-27-01",
    ]
    assert "N.D. Const. art. VI, § 28" not in result


def test_list_stops_at_a_signal():
    # (corpus) "25 U.S.C. §§ 1901-1963; see also N.D.C.C. ch. 27-19.1"
    result = norms("25 U.S.C. §§ 1901 through 1963; see also N.D.C.C. ch. 27-19.1.")
    assert "N.D.C.C. ch. 27-19.1" in result
    assert not any(n.startswith("25 U.S.C.") and n not in
                   ("25 U.S.C. § 1901", "25 U.S.C. § 1963") for n in result)


def test_list_stops_at_et_seq():
    # (corpus) "§§ 16.1–16–10, et seq."
    assert norms("N.D.C.C. §§ 16.1-16-10, et seq.") == ["N.D.C.C. § 16.1-16-10"]


def test_list_stops_at_a_case_name():
    # (corpus) "Sections 1–02–02, 1–02–03, N.D.C.C.; County of Stutsman v. ..."
    result = norms(
        "Sections 1-02-02, 1-02-03, N.D.C.C.; County of Stutsman v. State Historical Society"
    )
    assert result[:2] == ["N.D.C.C. § 1-02-02", "N.D.C.C. § 1-02-03"]


def test_singular_marker_does_not_expand():
    """A single "§" with a comma list is not a Bluebook list.

    The plural marker is the gate: R3.3 requires "§§" for multiple sections,
    so a singular symbol followed by numbers is far likelier to be prose or a
    string cite of something else.
    """
    assert norms("N.D.C.C. § 11-11-39, 11-11-43, and 28-34-01") == [
        "N.D.C.C. § 11-11-39"
    ]


def test_reporter_volume_is_not_a_truncated_member():
    result = norms("N.D.C.C. §§ 12-1-1, 5 N.W.2d 3 (N.D. 1942)")
    assert "N.D.C.C. § 12-1-5" not in result


def test_nd_reporter_volume_is_not_a_truncated_member():
    """"N.D." alone must not satisfy the code-attribution terminator."""
    result = norms("N.D.C.C. §§ 12-1-1, 5 N.D. 3 (1892)")
    assert "N.D.C.C. § 12-1-5" not in result


def test_page_reference_is_not_a_member():
    assert norms("N.D.C.C. §§ 28-27-01, at 14.") == ["N.D.C.C. § 28-27-01"]


def test_subdivision_is_not_a_new_section():
    # (corpus) "Sections 12.1–20–02(3) and (4), N.D.C.C."
    result = norms("Sections 12.1-20-02(3) and (4), N.D.C.C., define sexual contact.")
    assert result == ["N.D.C.C. § 12.1-20-02"]


def test_treatise_sections_are_not_ndcc():
    # (corpus) "§§ 9-23; 22 C. J. p. 158 et seq."
    assert norms("16 Am. Jur. 2d §§ 9-23; 22 C. J. p. 158 et seq.") == []


def test_other_states_code_is_not_ndcc():
    # (corpus) "Sections 36-2006 et seq., Oregon Code Annotated"
    assert norms("Sections 36-2006 et seq., Oregon Code Annotated, 1930.") == []


def test_revised_code_of_1943_is_not_ndcc():
    # (corpus) "Sections 12–2216 and 12–2217 RCND 1943."
    assert norms("Sections 12-2216 and 12-2217 RCND 1943.") == []


def test_rules_followed_by_a_year_is_not_a_rule():
    # (corpus) "Rules 1986 Desk Copy."
    assert norms("Rules 1986 Desk Copy. The relevancy of a document") == []


def test_expansion_never_crosses_a_sentence():
    text = "N.D.C.C. §§ 28-27-01 and 28-27-02. 11-11-43 was not cited."
    assert norms(text) == ["N.D.C.C. § 28-27-01", "N.D.C.C. § 28-27-02"]


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_expanded_members_are_flagged_with_their_anchor():
    cs = {c.normalized: c for c in cites("N.D.C.C. §§ 11-11-39, 11-11-43")}
    anchor = cs["N.D.C.C. § 11-11-39"]
    member = cs["N.D.C.C. § 11-11-43"]
    assert not anchor.components.get("enumerated")
    assert member.components.get("enumerated") is True
    assert member.components["enumerated_from"] == "N.D.C.C. § 11-11-39"


def test_expanded_members_carry_their_own_position():
    text = "under N.D.C.C. §§ 11-11-39, 11-11-43, and 28-34-01 the claim fails"
    cs = {c.normalized: c for c in cites(text)}
    for name in ("N.D.C.C. § 11-11-43", "N.D.C.C. § 28-34-01"):
        cite = cs[name]
        assert text[cite.position : cite.position + len(cite.raw_text)] == cite.raw_text
    assert cs["N.D.C.C. § 11-11-43"].position < cs["N.D.C.C. § 28-34-01"].position


def test_expanded_members_get_their_own_url():
    cs = {c.normalized: c for c in cites("N.D.C.C. §§ 11-11-39, 28-34-01")}
    url = cs["N.D.C.C. § 28-34-01"].sources[0].url
    assert "ndlegis.gov" in url
    assert "28-34-01" in url


@pytest.mark.parametrize(
    "text,member,fragment",
    [
        ("N.D.C.C. §§ 11-11-39, 28-34-01", "N.D.C.C. § 28-34-01", "t28c34.pdf#nameddest=28-34-01"),
        ("N.D.C.C. chs. 57-39.2, 57-40.2", "N.D.C.C. ch. 57-40.2", "t57c40-2.pdf"),
        ("N.D.A.C. §§ 75-02-04.1-01 and 75-02-04.1-02", "N.D.A.C. § 75-02-04.1-02", "75-02-04"),
        ("N.D. Const. art. VI, §§ 2 and 6", "N.D. Const. art. VI, § 6", "artvi/sec6"),
        # A rule's parts are joined with "-", so Rule 50 must not become "5-0".
        ("Rules 50 and 59, N.D.R.Civ.P.", "N.D.R.Civ.P. 50", "ndrcivp/50"),
        (
            "North Dakota Rules of Professional Conduct 1.1, 1.3 and 1.5 require",
            "N.D.R. Prof. Conduct 1.3",
            "ndrprofconduct/1-3",
        ),
        ("42 U.S.C. §§ 1983, 1988", "42 U.S.C. § 1988", "uscode/42/1988"),
    ],
)
def test_expanded_member_urls(text, member, fragment):
    cs = {c.normalized: c for c in cites(text)}
    assert cs[member].sources, f"{member} has no source URL"
    assert fragment in cs[member].sources[0].url


def test_expanded_members_keep_the_family_type():
    for text, expected in [
        ("N.D.C.C. §§ 11-11-39, 11-11-43", CitationType.STATUTE),
        ("N.D.A.C. §§ 75-02-04.1-01 and 75-02-04.1-02", CitationType.REGULATION),
        ("N.D. Const. art. VI, §§ 2 and 6", CitationType.CONSTITUTION),
        ("Rules 50 and 59, N.D.R.Civ.P.", CitationType.COURT_RULE),
    ]:
        members = [c for c in cites(text) if c.components.get("enumerated")]
        assert members, text
        assert all(c.cite_type == expected for c in members), text


@pytest.mark.parametrize(
    "text,member,expected_raw",
    [
        # A subdivision belongs to the member and is part of its span.
        ("N.D.C.C. §§ 27-20-02(5)(a) and 27-20-03(1).", "N.D.C.C. § 27-20-03", "27-20-03(1)"),
        ("N.D.A.C. §§ 59.5-03-03-02(1); 4-07-19-02(1).", "N.D.A.C. § 4-07-19-02", "4-07-19-02(1)"),
        # A trailing parenthetical that is NOT a subdivision stays outside.
        ("N.D.C.C. §§ 30.1-20-08 and 30.1-20-09 (U.P.C.3-909)", "N.D.C.C. § 30.1-20-09", "30.1-20-09"),
        ("See 42 U.S.C. §§ 402(a) and 416(l) (1994).", "42 U.S.C. § 416", "416(l)"),
    ],
)
def test_member_raw_text_span_is_tight(text, member, expected_raw):
    """``raw_text`` is what a consumer hyperlinks, so it must not over-reach."""
    cs = {c.normalized: c for c in cites(text)}
    assert cs[member].raw_text == expected_raw


def test_expansion_is_idempotent_across_repeated_lists():
    """The same list twice yields the same set, deduplicated by the scanner."""
    once = norms("N.D.C.C. §§ 28-27-01 and 28-27-02.")
    twice = norms(
        "N.D.C.C. §§ 28-27-01 and 28-27-02. Again, N.D.C.C. §§ 28-27-01 and 28-27-02."
    )
    assert once == twice


# ---------------------------------------------------------------------------
# Documented limitations
# ---------------------------------------------------------------------------


def test_subdivision_only_tail_is_not_expanded():
    """(corpus) "Rules 10(f) and (g), N.D.R.App.P."

    A tail that is a bare subdivision refers back to the SAME rule, so there is
    no second citation to emit. The anchor itself is not matched either, which
    is pre-existing behaviour of the rule patterns rather than something the
    expander controls; this test pins the current output so a future change to
    the rule patterns is a deliberate one.
    """
    assert norms("Rules 10(f) and (g), N.D.R.App.P.") == []
