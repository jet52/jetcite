"""Tests for the batch scanner."""

import pytest

from jetcite.scanner import lookup, scan_text


def test_scan_deduplication():
    text = "See 2024 ND 156, ¶ 12. The court in 2024 ND 156 also held..."
    results = scan_text(text)
    nd_cites = [r for r in results if r.normalized == "2024 ND 156"]
    assert len(nd_cites) == 1


def test_scan_multiple_types():
    text = (
        "Under 42 U.S.C. § 1983, the plaintiff sued. "
        "The court cited 2024 ND 156. "
        "See also N.D.C.C. § 1-02-13. "
    )
    results = scan_text(text)
    types = {r.cite_type.value for r in results}
    assert "statute" in types
    assert "case" in types


def test_scan_ordering():
    text = "First 2024 ND 156, then 42 U.S.C. § 1983."
    results = scan_text(text)
    # Results should be in document order
    assert results[0].position < results[1].position


def test_lookup_single():
    result = lookup("585 N.W.2d 123")
    assert result is not None
    assert result.cite_type.value == "case"


def test_lookup_no_match():
    result = lookup("not a citation")
    assert result is None


# --- Parallel citation detection ---

def test_parallel_neutral_and_nw():
    """Neutral citation followed by NW reporter should be linked."""
    text = "See 2024 ND 156, 10 N.W.3d 500."
    results = scan_text(text)
    nd_cite = next(r for r in results if r.normalized == "2024 ND 156")
    nw_cite = next(r for r in results if "N.W." in r.normalized)
    assert nw_cite.normalized in nd_cite.parallel_cites
    assert nd_cite.normalized in nw_cite.parallel_cites


def test_parallel_source_merging():
    """Parallel citations should share sources."""
    text = "See 2024 ND 156, 10 N.W.3d 500."
    results = scan_text(text)
    nd_cite = next(r for r in results if r.normalized == "2024 ND 156")
    # ND cite should have ndcourts opinion URL AND courtlistener
    source_names = {s.name for s in nd_cite.sources}
    assert "ndcourts" in source_names
    assert "courtlistener" in source_names


def test_parallel_with_pinpoint():
    """Parallel cite with pinpoint between them should still be detected."""
    text = "See 2024 ND 156, ¶ 12, 10 N.W.3d 500."
    results = scan_text(text)
    nd_cite = next(r for r in results if r.normalized == "2024 ND 156")
    nw_cite = next(r for r in results if "N.W." in r.normalized)
    assert nw_cite.normalized in nd_cite.parallel_cites


def test_no_parallel_across_sentences():
    """Citations in separate sentences should NOT be linked."""
    text = "See 2024 ND 156. The court also cited 585 N.W.2d 123."
    results = scan_text(text)
    nd_cite = next(r for r in results if r.normalized == "2024 ND 156")
    assert len(nd_cite.parallel_cites) == 0


def test_parallel_nw2d_and_nd_neutral():
    """NW2d followed by neutral citation (reversed order)."""
    text = "See 585 N.W.2d 123, 2000 ND 45."
    results = scan_text(text)
    nw_cite = next(r for r in results if "N.W." in r.normalized)
    nd_cite = next(r for r in results if r.normalized == "2000 ND 45")
    assert nd_cite.normalized in nw_cite.parallel_cites
    assert nw_cite.normalized in nd_cite.parallel_cites


def test_parallel_old_nd_reporter():
    """Old N.D. Reports citation paired with N.W. citation."""
    text = "See 50 N.D. 123, 195 N.W. 500."
    results = scan_text(text)
    nd_cite = next(r for r in results if r.normalized == "50 N.D. 123")
    nw_cite = next(r for r in results if r.normalized == "195 N.W. 500")
    assert nw_cite.normalized in nd_cite.parallel_cites
    assert nd_cite.normalized in nw_cite.parallel_cites


class TestTrailingFullCitePins:
    """Full-cite trailing page pins: "259 N.W.2d 621, 627 (N.D. 1977)"."""

    def test_reporter_cite_captures_trailing_pin(self):
        from jetcite.scanner import scan_text
        cites = scan_text(
            "State ex rel. Olson v. Maxwell, 259 N.W.2d 621, 627 (N.D. 1977).",
            resolve=False)
        c = next(x for x in cites if x.normalized == "259 N.W.2d 621")
        assert c.pinpoint == "at 627"

    def test_page_range_pin(self):
        from jetcite.scanner import scan_text
        cites = scan_text("Johnson v. Hassett, 217 N.W.2d 771, 775-76 (N.D. 1974).",
                          resolve=False)
        c = next(x for x in cites if x.normalized == "217 N.W.2d 771")
        assert c.pinpoint == "at 775-76"

    def test_following_cite_volume_is_not_a_pin(self):
        from jetcite.scanner import scan_text
        cites = scan_text("See 259 N.W.2d 621, 627 N.W.2d 100.", resolve=False)
        c = next(x for x in cites if x.normalized == "259 N.W.2d 621")
        assert c.pinpoint is None

    def test_scotus_parallel_pair_each_get_their_pin(self):
        from jetcite.scanner import scan_text
        cites = scan_text("Ng Fung Ho v. White, 259 U.S. 276, 284, "
                          "42 S. Ct. 492, 495 (1922).", resolve=False)
        by = {c.normalized: c for c in cites}
        assert by["259 U.S. 276"].pinpoint == "at 284"
        assert by["42 S. Ct. 492"].pinpoint == "at 495"

    def test_neutral_cite_paragraph_pin_untouched(self):
        from jetcite.scanner import scan_text
        cites = scan_text("Olson v. Olson, 2024 ND 156, ¶ 7, 10 N.W.3d 500.",
                          resolve=False)
        c = next(x for x in cites if x.normalized == "2024 ND 156")
        assert c.pinpoint == "¶ 7"

    def test_repeat_occurrence_gets_its_own_pin(self):
        from jetcite.scanner import scan_text
        cites = scan_text(
            "Maxwell, 259 N.W.2d 621, 627 (N.D. 1977). Text. "
            "Later, Maxwell, 259 N.W.2d 621, 630.",
            resolve=False, include_occurrences=True)
        pins = [c.pinpoint for c in cites if c.normalized == "259 N.W.2d 621"]
        assert pins == ["at 627", "at 630"]

    def test_footnote_pin(self):
        from jetcite.scanner import scan_text
        cites = scan_text("City of Mandan v. Fern, 501 N.W.2d 739, 744 n.3 "
                          "(N.D. 1993).", resolve=False)
        c = next(x for x in cites if x.normalized == "501 N.W.2d 739")
        assert c.pinpoint == "at 744 n.3"

    def test_multi_footnote_pin(self):
        from jetcite.scanner import scan_text
        cites = scan_text("Fern, 501 N.W.2d 739, 744 nn.3-4 (N.D. 1993).",
                          resolve=False)
        c = next(x for x in cites if x.normalized == "501 N.W.2d 739")
        assert c.pinpoint == "at 744 nn.3-4"

    def test_bare_n_word_is_not_a_footnote(self):
        from jetcite.scanner import scan_text
        cites = scan_text("See 259 N.W.2d 621, 627 not the page.",
                          resolve=False)
        c = next(x for x in cites if x.normalized == "259 N.W.2d 621")
        assert c.pinpoint is None


class TestParallelLinkAcrossPin:
    """A pinpoint between two parallel cites must not break the link.

    The separator between the pair carries the following citation's leading
    comma (", 691,"), which once survived the strip and failed the anchored
    pinpoint test. See _detect_parallel_citations in scanner.py.
    """

    @pytest.mark.parametrize("text, lead, parallel", [
        # The reported case: bare page pin, U.S. Reports + S. Ct.
        ("Whalen v. United States, 445 U.S. 684, 691, 100 S. Ct. 1432 (1980).",
         "445 U.S. 684", "100 S. Ct. 1432"),
        # Page range
        ("Whalen v. United States, 445 U.S. 684, 691-92, 100 S. Ct. 1432 (1980).",
         "445 U.S. 684", "100 S. Ct. 1432"),
        # En-dash range
        ("Whalen v. United States, 445 U.S. 684, 691–92, 100 S. Ct. 1432 (1980).",
         "445 U.S. 684", "100 S. Ct. 1432"),
        # "at" form
        ("Whalen v. United States, 445 U.S. 684, at 691, 100 S. Ct. 1432 (1980).",
         "445 U.S. 684", "100 S. Ct. 1432"),
        # Regression: ND neutral paragraph pin, which never broke
        ("Olson v. Olson, 2020 ND 30, ¶ 16, 938 N.W.2d 897.",
         "2020 ND 30", "938 N.W.2d 897"),
        # Regression: paragraph range
        ("Olson v. Olson, 2024 ND 156, ¶¶ 7-9, 10 N.W.3d 500.",
         "2024 ND 156", "10 N.W.3d 500"),
    ])
    def test_pin_between_parallels_still_links(self, text, lead, parallel):
        cites = scan_text(text, resolve=False)
        by = {c.normalized: c for c in cites}
        assert parallel in by[lead].parallel_cites
        assert lead in by[parallel].parallel_cites

    def test_three_member_group_chains_across_a_pin(self):
        """A pin must not change the shape of a three-cite group.

        Linking is pairwise over adjacent cites, so the group is a chain, not
        a clique. The point is that the pinned text produces the same chain as
        the unpinned text.
        """
        pinned = scan_text(
            "Whalen v. United States, 445 U.S. 684, 691, 100 S. Ct. 1432, "
            "63 L. Ed. 2d 715 (1980).", resolve=False)
        plain = scan_text(
            "Whalen v. United States, 445 U.S. 684, 100 S. Ct. 1432, "
            "63 L. Ed. 2d 715 (1980).", resolve=False)
        shape = {c.normalized: sorted(c.parallel_cites) for c in pinned}
        assert shape == {c.normalized: sorted(c.parallel_cites) for c in plain}
        assert shape == {
            "445 U.S. 684": ["100 S. Ct. 1432"],
            "100 S. Ct. 1432": ["445 U.S. 684", "63 L. Ed. 2d 715"],
            "63 L. Ed. 2d 715": ["100 S. Ct. 1432"],
        }

    def test_pin_keeps_its_own_pinpoint(self):
        """Linking the pair must not disturb the lead cite's pinpoint."""
        cites = scan_text(
            "Whalen v. United States, 445 U.S. 684, 691, 100 S. Ct. 1432 (1980).",
            resolve=False)
        by = {c.normalized: c for c in cites}
        assert by["445 U.S. 684"].pinpoint == "at 691"

    @pytest.mark.parametrize("text", [
        # Sentence break between the two cites
        "See 445 U.S. 684. 100 S. Ct. 1432 is a different case.",
        # Intervening clause, over the 40-character separator ceiling
        "See 445 U.S. 684, 691, which the court distinguished at some length "
        "in a later passage, 100 S. Ct. 1432.",
        # Intervening prose under the ceiling is still not a pinpoint
        "See 445 U.S. 684, 691, distinguished by, 100 S. Ct. 1432.",
    ])
    def test_non_parallel_pairs_stay_unlinked(self, text):
        cites = scan_text(text, resolve=False)
        by = {c.normalized: c for c in cites}
        assert by["445 U.S. 684"].parallel_cites == []
        assert by["100 S. Ct. 1432"].parallel_cites == []


class TestSemicolonIsNotAParallelSeparator:
    """A semicolon separates authorities, so it never joins parallel cites.

    What the source wrote is preserved — no link — and what it apparently
    meant is recorded in suspected_parallel_cites, the same statute the
    scanner applies to the court's own citation defects.

    Measured over 2,500 opinions of the ndlaw corpus (11,224 parallel links),
    only seven links crossed a semicolon. Six were genuine — five in the
    pre-1960 style that used a semicolon where modern form uses a comma, one a
    typo in a 2024 opinion — and one joined two different cases. Asserting any
    of them would misplace a consumer's badge on a live draft; recording all
    seven loses nothing.
    """

    @pytest.mark.parametrize("text, first, second", [
        # Bare semicolon between two cites of different cases
        ("See 2020 ND 30, ¶ 16, 938 N.W.2d 897; 2019 ND 12, ¶ 5.",
         "938 N.W.2d 897", "2019 ND 12"),
        # The measured false positive: a mangled "; ," separator
        ("2001 ND 138, ¶ 17, 631 N.W.2d 564; , 2000 ND 147, ¶ 9.",
         "631 N.W.2d 564", "2000 ND 147"),
        # Semicolon after a page pin — the comma-led form the both-ends strip
        # would otherwise let through
        ("Palmigiani v. D'Argenio, 234 Mass. 434, 436; 125 N.E. 592.",
         "234 Mass. 434", "125 N.E. 592"),
        # The pre-1960 semicolon-as-parallel style
        ("State v. Albertson, 20 N.D. 512; 128 N.W. 1122.",
         "20 N.D. 512", "128 N.W. 1122"),
        # A modern typo for the same thing (2002 ND 101, a real example)
        ("Hansen v. Scott, 2002 ND 101, ¶ 7; 645 N.W.2d 223.",
         "2002 ND 101", "645 N.W.2d 223"),
    ])
    def test_semicolon_pair_is_recorded_not_linked(self, text, first, second):
        cites = scan_text(text, resolve=False)
        by = {c.normalized: c for c in cites}
        assert second not in by[first].parallel_cites
        assert first not in by[second].parallel_cites
        # ...but not lost: recorded both ways.
        assert by[first].suspected_parallel_cites == [second]
        assert by[second].suspected_parallel_cites == [first]

    def test_comma_form_of_the_same_pair_links_and_suspects_nothing(self):
        """The comma spelling of the pre-1960 example is unaffected."""
        cites = scan_text("State v. Albertson, 20 N.D. 512, 128 N.W. 1122.",
                          resolve=False)
        by = {c.normalized: c for c in cites}
        assert by["20 N.D. 512"].parallel_cites == ["128 N.W. 1122"]
        assert by["128 N.W. 1122"].parallel_cites == ["20 N.D. 512"]
        assert by["20 N.D. 512"].suspected_parallel_cites == []
        assert by["128 N.W. 1122"].suspected_parallel_cites == []

    def test_a_suspicion_merges_nothing(self):
        """Recorded, never asserted: no sources pooled, no name inherited.

        The comma form of this pair gives the N.W. cite both the ndcourts
        source and the case name; the semicolon form must give it neither.
        """
        semi = scan_text("Hansen v. Scott, 2002 ND 101, ¶ 7; 645 N.W.2d 223.",
                         resolve=False)
        comma = scan_text("Hansen v. Scott, 2002 ND 101, ¶ 7, 645 N.W.2d 223.",
                          resolve=False)
        semi_nw = next(c for c in semi if c.normalized == "645 N.W.2d 223")
        comma_nw = next(c for c in comma if c.normalized == "645 N.W.2d 223")
        assert comma_nw.antecedent_name == "Hansen v. Scott"
        assert semi_nw.antecedent_name is None
        assert "ndcourts" in {s.name for s in comma_nw.sources}
        assert "ndcourts" not in {s.name for s in semi_nw.sources}

    def test_unrelated_cites_are_not_suspected(self):
        """A sentence break is not a punctuation slip — nothing is recorded."""
        cites = scan_text("See 445 U.S. 684. 100 S. Ct. 1432 is a different "
                          "case.", resolve=False)
        for c in cites:
            assert c.parallel_cites == []
            assert c.suspected_parallel_cites == []

    def test_serialization_carries_the_record(self):
        cites = scan_text("State v. Albertson, 20 N.D. 512; 128 N.W. 1122.",
                          resolve=False)
        by = {c.normalized: c for c in cites}
        d = by["20 N.D. 512"].to_dict()
        assert d["suspected_parallel_cites"] == ["128 N.W. 1122"]
        assert "parallel_cites" not in d
        # Absent, not empty, when there is nothing to record.
        plain = scan_text("See 2024 ND 156.", resolve=False)[0].to_dict()
        assert "suspected_parallel_cites" not in plain
