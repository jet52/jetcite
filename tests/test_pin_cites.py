"""Tests for Bluebook pin-cite short-form parsing and parent linking."""

from pathlib import Path

from jetcite.cache import citation_path
from jetcite.legacy import CASE_TYPES, PIN_CITE_TYPE, legacy_cite_type
from jetcite.patterns.pin_cites import PinCiteMatcher
from jetcite.scanner import scan_text

FIXTURES = Path(__file__).parent / "fixtures"


def _pins(citations):
    return [c for c in citations if c.is_pin_cite]


def _fulls(citations):
    return [c for c in citations if not c.is_pin_cite]


# ── Rule pins: bare "Rule N" attribution ladder ──────────────────────────────


def test_rule_pin_candidate_shape():
    results = [c for c in PinCiteMatcher().find_all("Under Rule 60(b), relief")
               if c.components.get("shape") == "rule_pin"]
    assert len(results) == 1
    pin = results[0]
    assert pin.components["rule"] == "60"
    assert pin.components["subdivision"] == "(b)"
    assert pin.pinpoint == "(b)"
    assert pin.cite_type.value == "court_rule"


def test_rule_pin_multipart_number():
    results = [c for c in PinCiteMatcher().find_all("Rule 8.3.1 provides")
               if c.components.get("shape") == "rule_pin"]
    assert len(results) == 1
    assert results[0].components["rule"] == "8.3.1"


def test_rule_pin_plural_not_matched():
    results = [c for c in PinCiteMatcher().find_all("Rules 12 and 56 apply")
               if c.components.get("shape") == "rule_pin"]
    assert results == []


def test_rule_pin_year_parenthetical_not_subdivision():
    results = [c for c in PinCiteMatcher().find_all("Rule 12(2007) discussion")
               if c.components.get("shape") == "rule_pin"]
    assert len(results) == 1
    assert "subdivision" not in results[0].components


def test_rule_pin_marker_attribution_links_to_full_cite():
    text = ("A motion under N.D.R.Civ.P. 60(b) must be timely. "
            "Under Rule 60(b), relief also requires diligence.")
    pins = _pins(scan_text(text, include_pin_cites=True))
    assert len(pins) == 1
    assert pins[0].parent_normalized == "N.D.R.Civ.P. 60"
    assert pins[0].components["attribution"] == "marker"
    assert pins[0].jurisdiction == "nd"
    assert any(s.name == "ndcourts" for s in pins[0].sources)


def test_rule_pin_trailing_spelled_marker_synthesizes_parent():
    text = "Rule 60(b) of the North Dakota Rules of Civil Procedure requires a motion."
    pins = _pins(scan_text(text, include_pin_cites=True))
    assert len(pins) == 1
    assert pins[0].parent_normalized == "N.D.R.Civ.P. 60"
    assert pins[0].components["attribution"] == "trailing"
    assert pins[0].jurisdiction == "nd"


def test_rule_pin_sole_set_links_to_later_full_cite():
    """Bare form first (e.g. under a section heading), full cite later."""
    text = ("Rule 29 requires an acquittal motion. "
            "We review a motion under N.D.R.Crim.P. 29 de novo.")
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized == "N.D.R.Crim.P. 29"
    assert pins[0].components["attribution"] == "sole_set"
    full = next(c for c in _fulls(citations)
                if c.normalized == "N.D.R.Crim.P. 29")
    assert pins[0].sources == full.sources


def test_rule_pin_federal_decoy_not_attributed_to_nd():
    """A bare Rule 12 after a federal-rules discussion must not link to the
    ND set; with no federal full cite to link, it is dropped."""
    text = ("We cited N.D.R.Civ.P. 12 before. Under the Federal Rules of "
            "Civil Procedure, dismissal is governed by Rule 12.")
    pins = _pins(scan_text(text, include_pin_cites=True))
    assert pins == []


def test_rule_pin_federal_decoy_links_to_federal_full_cite():
    text = ("Dismissal under Fed. R. Civ. P. 12(b)(6) is reviewed de novo. "
            "Rule 12 requires a short and plain statement of the defense.")
    pins = _pins(scan_text(text, include_pin_cites=True))
    assert len(pins) == 1
    assert pins[0].parent_normalized == "Fed. R. Civ. P. 12(b)(6)"
    assert pins[0].jurisdiction == "us"


def test_rule_pin_two_sets_no_marker_dropped():
    text = "Rule 12 governs. See N.D.R.Civ.P. 12; Fed. R. Civ. P. 12."
    pins = _pins(scan_text(text, include_pin_cites=True))
    assert pins == []


def test_rule_pin_conflicting_marker_dropped():
    """Nearest-marker attribution contradicted by the document's full cites
    (no N.D.R.Ct. 60 exists; 60 is cited under Civ.P.) — drop, don't guess."""
    text = ("See N.D.R.Civ.P. 60(b); N.D.R.Ct. 3.2. "
            "Under Rule 60(b), relief requires a motion.")
    pins = _pins(scan_text(text, include_pin_cites=True))
    assert pins == []


def test_rule_pin_chained_id_inherits_rule_parent():
    text = ("A motion under N.D.R.Civ.P. 60(b) must be timely. "
            "Under Rule 60(b), relief requires diligence. "
            "Id. also lists the grounds.")
    pins = _pins(scan_text(text, include_pin_cites=True))
    assert len(pins) == 2
    assert all(p.parent_normalized == "N.D.R.Civ.P. 60" for p in pins)


def test_rule_pin_default_scan_unchanged():
    text = ("A motion under N.D.R.Civ.P. 60(b) must be timely. "
            "Under Rule 60(b), relief also requires diligence.")
    citations = scan_text(text)
    assert [c.normalized for c in citations] == ["N.D.R.Civ.P. 60"]


def test_rule_pin_legacy_dict():
    from jetcite.legacy import to_legacy_dict

    text = ("A motion under N.D.R.Civ.P. 60(b) must be timely. "
            "Under Rule 60(b), relief also requires diligence.")
    pin = _pins(scan_text(text, include_pin_cites=True))[0]
    entry = to_legacy_dict(pin, Path("/tmp/refs"))
    assert entry["cite_type"] == PIN_CITE_TYPE
    assert entry["parent_normalized"] == "N.D.R.Civ.P. 60"
    assert entry["pinpoint"] == "(b)"
    assert entry["local_path"] is None


# ── Matcher unit tests: shape 1 (reporter pins) ──────────────────────────────


def test_f3d_pin():
    results = PinCiteMatcher().find_all("491 F.3d at 363")
    assert len(results) == 1
    pin = results[0]
    assert pin.is_pin_cite
    assert pin.components["reporter"] == "F.3d"
    assert pin.components["volume"] == "491"
    assert pin.pin_page == "363"
    assert pin.pinpoint == "at 363"


def test_so_3d_pin():
    results = PinCiteMatcher().find_all("409 So. 3d at 188")
    assert len(results) == 1
    assert results[0].components["reporter"] == "So. 3d"
    assert results[0].pin_page == "188"


def test_nw_first_series_pin():
    results = PinCiteMatcher().find_all("67 N.W. at 75")
    assert len(results) == 1
    assert results[0].components["reporter"] == "N.W."


def test_us_reports_pin():
    results = PinCiteMatcher().find_all("595 U.S. at 12")
    assert len(results) == 1
    assert results[0].components["reporter"] == "U.S."


def test_f_supp_2d_pin():
    results = PinCiteMatcher().find_all("100 F. Supp. 2d at 50")
    assert len(results) == 1
    assert results[0].components["reporter"] == "F. Supp. 2d"


def test_pin_page_range():
    results = PinCiteMatcher().find_all("491 F.3d at 363-65")
    assert len(results) == 1
    assert results[0].pin_page == "363-65"


def test_nd_neutral_at_para_pin():
    results = PinCiteMatcher().find_all("2024 ND 156 at ¶ 12")
    assert len(results) == 1
    pin = results[0]
    assert pin.components["year"] == "2024"
    assert pin.components["number"] == "156"
    assert pin.pin_paragraph == "12"
    assert pin.pinpoint == "¶ 12"


# ── Matcher unit tests: Id. forms ────────────────────────────────────────────


def test_id_at_page():
    results = PinCiteMatcher().find_all("The court agreed. Id. at 363.")
    assert len(results) == 1
    assert results[0].components["shape"] == "id"
    assert results[0].pin_page == "363"


def test_id_paragraph():
    results = PinCiteMatcher().find_all("So held below. Id. ¶ 14.")
    assert len(results) == 1
    assert results[0].pin_paragraph == "14"


def test_lowercase_id_in_parenthetical():
    results = PinCiteMatcher().find_all("(citing id. at 5)")
    assert len(results) == 1
    assert results[0].pin_page == "5"


def test_markdown_italic_id():
    results = PinCiteMatcher().find_all("So held below. *Id.* at 5.")
    assert len(results) == 1
    assert results[0].pin_page == "5"


def test_bare_id_sentence_start():
    results = PinCiteMatcher().find_all("The court agreed. Id.")
    assert len(results) == 1
    assert results[0].pin_page is None
    assert results[0].pin_paragraph is None


def test_bare_id_not_word_tail():
    """'valid.' / 'said.' must not match as Id."""
    assert PinCiteMatcher().find_all("The argument is valid. More text.") == []
    assert PinCiteMatcher().find_all("That is what she said. More text.") == []


def test_bare_lowercase_id_midsentence_rejected():
    """A bare lowercase 'id.' without parenthetical/signal context is noise."""
    results = PinCiteMatcher().find_all("the same id. number as before")
    assert results == []


# ── Matcher unit tests: negatives ────────────────────────────────────────────


def test_prose_at_number_not_matched():
    assert PinCiteMatcher().find_all(
        "The motion was argued at 363 before the panel.") == []


def test_street_address_not_matched():
    assert PinCiteMatcher().find_all("He lived at 363 Main Street.") == []


def test_full_cite_not_matched_as_pin():
    """A full cite has no 'at' — the pin patterns must not fire on it."""
    assert PinCiteMatcher().find_all("491 F.3d 355") == []
    assert PinCiteMatcher().find_all("Niemeyer v. Niemeyer, 2024 ND 156, ¶ 8") == []


# ── Scanner: linking, dedup invariants, source inheritance ───────────────────


def test_default_scan_unchanged_by_pins():
    """Without the flag, a doc with full + pin yields exactly the full cite."""
    text = "Goss, 491 F.3d 355 (8th Cir. 2007). Later: Goss, 491 F.3d at 363."
    citations = scan_text(text)
    assert [c.normalized for c in citations] == ["491 F.3d 355"]
    assert all(not c.is_pin_cite for c in citations)


def test_reporter_pin_links_to_parent():
    text = "Goss, 491 F.3d 355 (8th Cir. 2007). Later: Goss, 491 F.3d at 363."
    citations = scan_text(text, include_pin_cites=True)
    fulls, pins = _fulls(citations), _pins(citations)
    assert [c.normalized for c in fulls] == ["491 F.3d 355"]
    assert len(pins) == 1
    pin = pins[0]
    assert pin.parent_normalized == "491 F.3d 355"
    assert pin.position > fulls[0].position
    # Shape 2: the short-form name preceding the pin is captured
    assert pin.antecedent_name == "Goss"
    # Sources inherited from the parent
    assert [s.url for s in pin.sources] == [s.url for s in fulls[0].sources]
    assert pin.sources


def test_name_pin_resolves_via_name_map():
    text = (
        "Goss Int'l Corp. v. Man Roland Druckmaschinen AG, 491 F.3d 355 "
        "(8th Cir. 2007). The principle is settled. Goss at 365."
    )
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized == "491 F.3d 355"
    assert pins[0].pin_page == "365"


def test_unresolvable_name_pin_dropped():
    text = "The principle is settled. Idaho at 22 discusses nothing."
    citations = scan_text(text, include_pin_cites=True)
    assert _pins(citations) == []


def test_unresolved_reporter_pin_kept_as_warning():
    """Explicit pin syntax with no antecedent is a brief-writing error."""
    text = "As the court held, 491 F.3d at 363."
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized is None
    assert pins[0].sources == []


def test_id_resolves_to_preceding_cite():
    text = "Tracey v. Tracey, 2023 ND 219, ¶ 9. Id. at ¶ 14."
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized == "2023 ND 219"
    assert pins[0].pin_paragraph == "14"


def test_id_chain_resolves_transitively():
    text = "Goss, 491 F.3d 355 (8th Cir. 2007). Id. at 359. Id. at 363."
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 2
    assert all(p.parent_normalized == "491 F.3d 355" for p in pins)
    # Chained pin inherits the full parent's sources, not the prior pin's span
    assert pins[1].sources == pins[0].sources


def test_id_after_parallel_pair_resolves():
    """A parallel pair is one authority — not an ambiguous antecedent."""
    text = "Niemeyer v. Niemeyer, 2024 ND 156, ¶ 8, 9 N.W.3d 100. Id. ¶ 9."
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized in ("2024 ND 156", "9 N.W.3d 100")


def test_id_after_string_cite_unresolved():
    text = "Apple v. Bell, 1 N.W.2d 1; Crow v. Dove, 2 N.W.2d 2. Id. at 3."
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized is None


def test_id_after_string_cite_with_parentheticals_unresolved():
    """Court/date parentheticals don't disguise a string cite."""
    text = (
        "Apple v. Bell, 1 N.W.2d 1 (N.D. 1941); "
        "Crow v. Dove, 2 N.W.2d 2 (N.D. 1941). Id. at 3."
    )
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized is None


def test_id_after_rule_resolves_to_rule_not_case():
    """Id. whose true antecedent is a court rule must not skip back to the
    nearest case (TODO: Id.-after-rule bug, 2026-07-20)."""
    text = (
        "In State v. Gonzalez, 2024 ND 4, ¶ 6, 1 N.W.3d 919, we applied the "
        "rule. Relief requires a motion under N.D.R.Civ.P. 60(b). Id. "
        "requires the motion to be made within a reasonable time."
    )
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized == "N.D.R.Civ.P. 60"
    assert pins[0].jurisdiction == "nd"


def test_id_after_statute_resolves_to_statute():
    text = (
        "We construed the statute in Schmidt v. Schmidt, 2023 ND 100, ¶ 5. "
        "Custody is governed by N.D.C.C. § 14-09-06.2. Id. lists the "
        "best-interest factors."
    )
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized == "N.D.C.C. § 14-09-06.2"


def test_id_after_constitution_resolves_to_constitution():
    text = (
        "See Riemers v. State, 2006 ND 162. The right is secured by "
        "N.D. Const. art. I, § 20. Id. also limits the remedy."
    )
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized == "N.D. Const. art. I, § 20"


def test_id_chain_through_rule_parent():
    text = (
        "Relief requires a motion under N.D.R.Civ.P. 60(b). Id. requires "
        "a reasonable time. Id. also lists the grounds."
    )
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 2
    assert all(p.parent_normalized == "N.D.R.Civ.P. 60" for p in pins)


def test_bare_id_after_rule_inherits_no_pinpoint():
    """Rule subdivisions aren't page/¶ pinpoints — a bare Id. after a rule
    carries no pinpoint rather than a bogus inherited one."""
    text = "Relief requires a motion under N.D.R.Civ.P. 60(b). Id. so provides."
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].pin_page is None
    assert pins[0].pin_paragraph is None


def test_id_after_rule_inherits_rule_sources():
    text = "Relief requires a motion under N.D.R.Civ.P. 60(b). Id. so provides."
    citations = scan_text(text, include_pin_cites=True)
    rule = next(c for c in _fulls(citations) if c.normalized == "N.D.R.Civ.P. 60")
    pin = _pins(citations)[0]
    assert pin.sources == rule.sources
    assert any(s.name == "ndcourts" for s in pin.sources)


def test_id_after_rule_string_cite_unresolved():
    """Two rules in a string cite are as ambiguous as two cases."""
    text = "See N.D.R.Civ.P. 60(b); N.D.R.Ct. 3.2. Id. requires a motion."
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized is None


def test_id_after_mixed_case_and_rule_string_cite_unresolved():
    text = (
        "See State v. Gonzalez, 2024 ND 4; N.D.R.Civ.P. 60(b). Id. requires "
        "a motion."
    )
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized is None


def test_id_after_statute_recitation_resolves_to_statute():
    """A re-cited statute is deduped from output, but its position must
    still anchor a following Id. — not the nearer emitted case cite."""
    text = (
        "Custody is governed by N.D.C.C. § 14-09-06.2. "
        "See State v. Gonzalez, 2024 ND 4, ¶ 6. "
        "Relief also requires N.D.C.C. § 14-09-06.2. Id. lists the factors."
    )
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized == "N.D.C.C. § 14-09-06.2"
    # Only the first statute occurrence is emitted
    fulls = [c.normalized for c in _fulls(citations)]
    assert fulls.count("N.D.C.C. § 14-09-06.2") == 1


def test_id_after_rule_recitation_resolves_to_rule():
    text = (
        "A motion under N.D.R.Civ.P. 60(b) must be timely. "
        "See State v. Gonzalez, 2024 ND 4, ¶ 6. "
        "Relief requires a motion under N.D.R.Civ.P. 60(b). "
        "Id. requires a reasonable time."
    )
    pins = _pins(scan_text(text, include_pin_cites=True))
    assert len(pins) == 1
    assert pins[0].parent_normalized == "N.D.R.Civ.P. 60"


def test_id_after_case_recitation_without_occurrences_flag():
    """Even without include_occurrences, an Id. after a re-cited case must
    anchor to the re-citation's position and inherit its pinpoint."""
    text = (
        "Tracey v. Tracey, 2023 ND 219, ¶ 9. "
        "See also State v. Gonzalez, 2024 ND 4, ¶ 6. "
        "Tracey, 2023 ND 219, ¶ 14. Id."
    )
    citations = scan_text(text, include_pin_cites=True)
    pins = [p for p in _pins(citations) if p.components.get("shape") == "id"]
    assert len(pins) == 1
    assert pins[0].parent_normalized == "2023 ND 219"
    assert pins[0].pin_paragraph == "14"


def test_bare_id_with_no_antecedent_dropped():
    text = "Id. is a Latin abbreviation."
    citations = scan_text(text, include_pin_cites=True)
    assert _pins(citations) == []


def test_id_at_with_no_antecedent_kept():
    text = "Id. at 5."
    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    assert len(pins) == 1
    assert pins[0].parent_normalized is None


def test_neutral_at_pin_after_earlier_full_cite():
    """Second occurrence in 'at ¶' form becomes a pin on the earlier cite."""
    text = "Niemeyer v. Niemeyer, 2024 ND 156, ¶ 8. Later: 2024 ND 156 at ¶ 14."
    citations = scan_text(text, include_pin_cites=True)
    fulls, pins = _fulls(citations), _pins(citations)
    assert [c.normalized for c in fulls] == ["2024 ND 156"]
    assert len(pins) == 1
    assert pins[0].parent_normalized == "2024 ND 156"
    assert pins[0].pin_paragraph == "14"


def test_first_occurrence_at_form_is_full_cite_not_pin():
    """When the 'at ¶' form is the first occurrence, it parses as a full cite
    (widened neutral pattern) and the overlapping pin candidate is dropped."""
    text = "The court so held. 2024 ND 156 at ¶ 12."
    citations = scan_text(text, include_pin_cites=True)
    assert [c.normalized for c in _fulls(citations)] == ["2024 ND 156"]
    assert _fulls(citations)[0].pinpoint == "¶ 12"
    assert _pins(citations) == []


# ── End-to-end over the fixture brief ────────────────────────────────────────


def test_fixture_brief_end_to_end():
    text = (FIXTURES / "pin_cite_brief.txt").read_text()

    # Default scan: no pins, no phantom cites
    default = scan_text(text)
    norms = [c.normalized for c in default]
    assert "491 F.3d 355" in norms
    assert "2024 ND 156" in norms
    assert "9 N.W.3d 100" in norms
    assert all(not c.is_pin_cite for c in default)

    citations = scan_text(text, include_pin_cites=True)
    pins = _pins(citations)
    by_norm = {p.normalized: p for p in pins}

    # Decoys produced nothing
    assert not any("363 Main" in p.normalized for p in pins)
    assert not any(p.normalized.startswith(("Smith", "Idaho")) for p in pins)

    # Shape 1 + 2: Goss reporter pin
    goss_pin = by_norm["491 F.3d at 363"]
    assert goss_pin.parent_normalized == "491 F.3d 355"

    # Shape 3: bare-name pins
    assert by_norm["Goss at 365"].parent_normalized == "491 F.3d 355"
    assert by_norm["Niemeyer, ¶ 12"].parent_normalized in (
        "2024 ND 156", "9 N.W.3d 100")

    # Neutral "at ¶" short form linked to the earlier full cite
    nd_pin = by_norm["2024 ND 156 at ¶ 14"]
    assert nd_pin.parent_normalized == "2024 ND 156"

    # Id. chain resolves transitively through the neutral pin
    id_pins = [p for p in pins if p.components.get("shape") == "id"]
    assert len(id_pins) == 2
    assert all(p.parent_normalized == "2024 ND 156" for p in id_pins)


# ── Legacy / cache invariants ────────────────────────────────────────────────


def test_pin_cite_legacy_type_and_cache():
    text = "Goss, 491 F.3d 355 (8th Cir. 2007). Id. at 359."
    citations = scan_text(text, include_pin_cites=True)
    pin = _pins(citations)[0]
    assert legacy_cite_type(pin) == PIN_CITE_TYPE
    assert PIN_CITE_TYPE not in CASE_TYPES
    assert citation_path(pin) is None


def test_to_dict_pin_keys_only_on_pins():
    text = "Goss, 491 F.3d 355 (8th Cir. 2007). Id. at 359."
    citations = scan_text(text, include_pin_cites=True)
    full_d = _fulls(citations)[0].to_dict()
    pin_d = _pins(citations)[0].to_dict()
    assert "is_pin_cite" not in full_d
    assert "parent_normalized" not in full_d
    assert pin_d["is_pin_cite"] is True
    assert pin_d["parent_normalized"] == "491 F.3d 355"
    assert pin_d["pin_page"] == "359"


class TestParallelPairPinLinking:
    """Pins after a parallel pair link to the pagination-matching member,
    not the textually nearest (trailing reporter) one."""

    ND_PAIR = (
        "\"A trial court has broad discretion in fixing a criminal "
        "sentence.\" State v. Gonzalez, 2024 ND 4, ¶ 6, 1 N.W.3d 919. "
        "Our review is generally confined to the statutory limits. "
    )

    def _pins(self, text):
        from jetcite import scan_text
        return [c for c in scan_text(text, resolve=False, include_pin_cites=True)
                if c.is_pin_cite]

    def test_bare_id_links_to_neutral_primary(self):
        pins = self._pins(self.ND_PAIR + "Id.; see also State v. Maher, "
                          "2026 ND 35, ¶ 7, 31 N.W.3d 619.")
        bare = next(p for p in pins if p.raw_text == "Id.")
        assert bare.parent_normalized == "2024 ND 4"
        assert bare.sources and bare.sources[0].name == "ndcourts"

    def test_paragraph_id_links_to_neutral_primary(self):
        pins = self._pins(self.ND_PAIR + "Id. ¶ 9.")
        pin = next(p for p in pins if p.pin_paragraph == "9")
        assert pin.parent_normalized == "2024 ND 4"

    def test_page_id_links_to_reporter(self):
        pins = self._pins(self.ND_PAIR + "Id. at 921.")
        pin = next(p for p in pins if p.pin_page == "921")
        assert pin.parent_normalized == "1 N.W.3d 919"

    def test_name_paragraph_pin_links_to_neutral(self):
        # Civil caption: the antecedent-name key is the first party, so a
        # name pin resolves ("Niemeyer"); criminal "State v. X" captions
        # key on "State" and are out of scope here.
        text = ("Niemeyer v. Niemeyer, 2024 ND 156, ¶ 8, 9 N.W.3d 100, "
                "requires specific findings. More discussion follows. "
                "Niemeyer, ¶ 12.")
        pins = self._pins(text)
        pin = next(p for p in pins if p.pin_paragraph == "12")
        assert pin.parent_normalized == "2024 ND 156"

    def test_chained_id_inherits_neutral(self):
        pins = self._pins(self.ND_PAIR + "Id. ¶ 9. More text. Id.")
        chained = [p for p in pins if p.raw_text == "Id."]
        assert chained and all(p.parent_normalized == "2024 ND 4" for p in chained)

    def test_scotus_page_id_prefers_us_reports(self):
        text = ("Mapp v. Ohio, 367 U.S. 643, 81 S. Ct. 1684 (1961), applied "
                "the exclusionary rule to the states. Id. at 655.")
        pins = self._pins(text)
        pin = next(p for p in pins if p.pin_page == "655")
        assert pin.parent_normalized == "367 U.S. 643"

    def test_regional_only_case_unchanged(self):
        text = ("Hogen v. Hogen, 226 N.W.2d 640 (N.D. 1975), set the "
                "framework. Id. at 643.")
        pins = self._pins(text)
        pin = next(p for p in pins if p.pin_page == "643")
        assert pin.parent_normalized == "226 N.W.2d 640"


class TestCriminalCaptionNamePins:
    """Defendant-name short forms after "State v. X" captions resolve."""

    def _pins(self, text):
        from jetcite import scan_text
        return [c for c in scan_text(text, resolve=False, include_pin_cites=True)
                if c.is_pin_cite]

    def test_defendant_paragraph_pin_resolves(self):
        text = ("State v. Gonzalez, 2024 ND 4, ¶ 6, 1 N.W.3d 919, governs "
                "sentencing review. More discussion follows. Gonzalez, ¶ 9.")
        pins = self._pins(text)
        pin = next(p for p in pins if p.pin_paragraph == "9")
        # parallel-pair preference applies on top: ¶ pin → neutral primary
        assert pin.parent_normalized == "2024 ND 4"

    def test_defendant_page_pin_resolves(self):
        text = ("State v. Himmerick, 499 N.W.2d 568 (N.D. 1993), controls. "
                "The reasoning is set out there. Himmerick at 571.")
        pins = self._pins(text)
        pin = next(p for p in pins if p.pin_page == "571")
        assert pin.parent_normalized == "499 N.W.2d 568"

    def test_individual_surname_is_last_word(self):
        text = ("Energy Co. v. Pat Gion, 2026 ND 999, ¶ 3, holds otherwise. "
                "We are not persuaded. Gion, ¶ 5.")
        pins = self._pins(text)
        pin = next(p for p in pins if p.pin_paragraph == "5")
        assert pin.parent_normalized == "2026 ND 999"

    def test_first_party_short_form_still_resolves(self):
        text = ("Goss Int'l Corp. v. Man Roland Druckmaschinen AG, 491 F.3d "
                "355 (8th Cir. 2007), counsels caution. Goss at 363.")
        pins = self._pins(text)
        pin = next(p for p in pins if p.pin_page == "363")
        assert pin.parent_normalized == "491 F.3d 355"

    def test_unrelated_name_still_drops(self):
        text = ("State v. Gonzalez, 2024 ND 4, ¶ 6, governs. "
                "The brief argued Pemberton at 363 was wrongly decided.")
        pins = self._pins(text)
        assert not any(p.components.get("shape") == "name_pin" for p in pins)


class TestBareIdPinpointInheritance:
    """A bare Id. adopts the antecedent's pinpoint (same authority, same
    page/paragraph), marked as inherited for verification."""

    def _pins(self, text, **kw):
        from jetcite import scan_text
        kw.setdefault("resolve", False)
        kw.setdefault("include_pin_cites", True)
        return [c for c in scan_text(text, **kw) if c.is_pin_cite]

    def test_bare_id_inherits_neutral_paragraph(self):
        text = ("State v. Gonzalez, 2024 ND 4, ¶ 6, 1 N.W.3d 919. Our "
                "review is confined to the statutory limits. Id.")
        pin = next(p for p in self._pins(text) if p.raw_text == "Id.")
        assert pin.parent_normalized == "2024 ND 4"
        assert pin.pin_paragraph == "6"
        assert pin.pinpoint == "¶ 6"
        assert pin.components.get("pinpoint_inherited") is True

    def test_bare_id_inherits_prior_pin_paragraph(self):
        text = ("Tracey v. Tracey, 2023 ND 219, ¶ 5. Id. ¶ 9. "
                "More discussion. Id.")
        pins = self._pins(text)
        bare = [p for p in pins if p.raw_text == "Id."
                and p.components.get("pinpoint_inherited")]
        assert len(bare) == 1
        assert bare[0].pin_paragraph == "9"

    def test_bare_id_inherits_prior_pin_page(self):
        text = ("Goss, 491 F.3d 355 (8th Cir. 2007). Id. at 363. "
                "The court agreed. Id.")
        pins = self._pins(text)
        bare = next(p for p in pins if p.components.get("pinpoint_inherited"))
        assert bare.pin_page == "363"
        assert bare.pinpoint == "at 363"

    def test_bare_id_inherits_repeat_paragraph(self):
        text = ("Niemeyer v. Niemeyer, 2024 ND 156, ¶ 8, holds so. "
                "Later: Niemeyer, 2024 ND 156, ¶ 12. Id.")
        pins = self._pins(text, include_occurrences=True)
        bare = next(p for p in pins if p.raw_text == "Id.")
        assert bare.pin_paragraph == "12"
        assert bare.parent_normalized == "2024 ND 156"

    def test_explicit_id_pinpoint_not_overridden(self):
        text = "Tracey v. Tracey, 2023 ND 219, ¶ 5. Id. ¶ 14."
        pin = next(p for p in self._pins(text) if p.pin_paragraph == "14")
        assert not pin.components.get("pinpoint_inherited")

    def test_bare_id_after_unpinpointed_cite_stays_bare(self):
        text = "The rule comes from Tracey v. Tracey, 2023 ND 219. Id."
        pin = next(p for p in self._pins(text) if p.raw_text == "Id.")
        assert pin.pin_paragraph is None and pin.pin_page is None
        assert not pin.components.get("pinpoint_inherited")

    def test_legacy_dict_marks_inherited(self, tmp_path):
        from jetcite import scan_text
        from jetcite.legacy import to_legacy_dict
        text = "State v. Gonzalez, 2024 ND 4, ¶ 6, 1 N.W.3d 919. Id."
        cites = scan_text(text, resolve=False, include_pin_cites=True)
        pin = next(c for c in cites if c.is_pin_cite)
        entry = to_legacy_dict(pin, tmp_path)
        assert entry["pin_paragraph"] == "6"
        assert entry["pinpoint_inherited"] is True


class TestQuotedMatterAntecedents:
    """Citations inside quoted matter cannot capture a following Id."""

    # A recurring drafting pattern: an id. after a quotation that itself
    # contains a citable reference must chain past the quote to the case.
    # (The quoted sentence is from Snyder's Drug Stores, 219 N.W.2d 140,
    # 146 (N.D. 1974) — a published opinion.)
    TEXT = (
        "Snyder’s Drug Stores v. N.D. State Bd. of Pharmacy, "
        "219 N.W.2d 140 (N.D. 1974). "
        "The court said: “For the purposes of this case, we consider "
        "Section 20 of the North Dakota Constitution to be similar,” "
        "id. at 146, and later “we conclude there is no compelling reason "
        "to do so,” id. at 150. A further point. Id.\n"
    )

    def _pins(self, text):
        from jetcite.scanner import scan_text
        return [c for c in scan_text(text, resolve=False,
                                     include_pin_cites=True)
                if c.is_pin_cite]

    def test_id_skips_citation_inside_quote(self):
        pins = self._pins(self.TEXT)
        at146 = next(p for p in pins if "146" in p.raw_text)
        assert at146.parent_normalized == "219 N.W.2d 140"

    def test_chained_ids_follow_the_corrected_parent(self):
        pins = self._pins(self.TEXT)
        assert [p.parent_normalized for p in pins] == ["219 N.W.2d 140"] * 3

    def test_quote_still_cited_as_its_own_entry(self):
        from jetcite.scanner import scan_text
        cites = scan_text(self.TEXT, resolve=False)
        assert any("N.D. Const." in c.normalized or "Section 20" in c.raw_text
                   for c in cites)

    def test_page_pin_skips_non_case_antecedent_outside_quotes(self):
        # No quotation marks at all (the unmarked-block-quote scenario):
        # the type guard alone must route a page pin past the constitution.
        text = ("State v. Doe, 100 N.W.2d 100 (N.D. 1960). Under "
                "Section 20 of the North Dakota Constitution the rule "
                "differs. Id. at 105.\n")
        pins = self._pins(text)
        assert pins[0].parent_normalized == "100 N.W.2d 100"

    def test_bare_id_still_takes_nearest_unquoted_antecedent(self):
        # A bare Id. (no page pin) after an unquoted constitution cite is
        # legitimate Bluebook usage and must keep resolving to it.
        text = ("Under Section 20 of the North Dakota Constitution the "
                "rule differs. Id.\n")
        pins = self._pins(text)
        assert pins and pins[0].parent_normalized is not None
        assert "Const" in pins[0].parent_normalized

    def test_unclosed_quote_extends_to_line_end(self):
        from jetcite.scanner import _quoted_spans
        text = "Before “an open quote with no close\nnext paragraph.\n"
        spans = _quoted_spans(text)
        assert spans == [(7, text.index("\n"))]
