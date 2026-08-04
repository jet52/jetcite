"""Tests for the batch scanner."""

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
