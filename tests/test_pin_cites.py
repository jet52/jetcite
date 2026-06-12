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
