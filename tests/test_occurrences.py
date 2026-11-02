"""Tests for occurrence-level scanning (include_occurrences=True).

Repeat full-form case citations — the second and later textual appearances
of a normalized form, e.g. a short cite written out as "Olson, 2024 ND 156,
¶ 12" — must surface as their own entries so a reviewer can validate each
proposition and pinpoint individually.
"""

from pathlib import Path

from jetcite import scan_text
from jetcite.legacy import add_parallel_info, to_legacy_dict

DRAFT = (
    "We held the statute unambiguous. Olson v. Estate of Olson, 2024 ND 156, "
    "¶ 7, 10 N.W.3d 500. Later discussion follows here. "
    "See Olson, 2024 ND 156, ¶ 12. "
    "More text. Olson, ¶ 19. "
    "Also 2024 ND 156 at ¶ 21. Then Id. ¶ 23. "
    "A second case, Smith v. Jones, 2023 ND 44, ¶ 3. Id."
)


def _scan(text=DRAFT, **kw):
    kw.setdefault("resolve", False)
    kw.setdefault("include_occurrences", True)
    return scan_text(text, **kw)


class TestRepeatCapture:
    def test_comma_form_repeat_captured_with_pinpoint(self):
        cites = _scan()
        repeats = [c for c in cites if c.is_repeat]
        olson_12 = [c for c in repeats if c.pinpoint == "¶ 12"]
        assert len(olson_12) == 1
        rep = olson_12[0]
        assert rep.normalized == "2024 ND 156"
        assert rep.parent_normalized == "2024 ND 156"

    def test_repeat_links_to_first_occurrence_position(self):
        cites = _scan()
        primary = next(c for c in cites
                       if c.normalized == "2024 ND 156" and not c.is_repeat)
        rep = next(c for c in cites if c.is_repeat and c.pinpoint == "¶ 12")
        assert rep.components["parent_position"] == primary.position
        assert rep.position > primary.position

    def test_at_para_form_yields_single_entry(self):
        # "2024 ND 156 at ¶ 21" matches both the full neutral pattern (as a
        # repeat) and the pin matcher; the span-overlap guard must leave
        # exactly one entry for the occurrence.
        cites = _scan(include_pin_cites=True)
        at_21 = [c for c in cites if c.pinpoint == "¶ 21"]
        assert len(at_21) == 1
        assert at_21[0].is_repeat
        assert not at_21[0].is_pin_cite

    def test_id_resolves_through_repeat_to_primary(self):
        cites = _scan(include_pin_cites=True)
        id_23 = next(c for c in cites if c.is_pin_cite and c.pin_paragraph == "23")
        assert id_23.parent_normalized == "2024 ND 156"

    def test_default_mode_unchanged(self):
        cites = scan_text(DRAFT, resolve=False)
        assert not any(c.is_repeat for c in cites)
        norms = [c.normalized for c in cites]
        assert norms.count("2024 ND 156") == 1

    def test_positions_sorted(self):
        cites = _scan(include_pin_cites=True)
        positions = [c.position for c in cites]
        assert positions == sorted(positions)


class TestRepeatSources:
    def test_repeat_inherits_primary_sources(self):
        cites = _scan()
        primary = next(c for c in cites
                       if c.normalized == "2024 ND 156" and not c.is_repeat)
        rep = next(c for c in cites if c.is_repeat and c.pinpoint == "¶ 12")
        assert [s.url for s in rep.sources] == [s.url for s in primary.sources]

    def test_repeat_inherits_local_cache_source(self, tmp_path):
        refs = tmp_path / "refs"
        opin = refs / "opin" / "ND" / "2024"
        opin.mkdir(parents=True)
        (opin / "2024ND156.md").write_text("[¶ 12] Cited paragraph.")
        cites = _scan(refs_dir=refs)
        rep = next(c for c in cites if c.is_repeat and c.pinpoint == "¶ 12")
        assert any(s.name == "local" for s in rep.sources)

    def test_repeat_never_maps_to_cache_path(self):
        from jetcite.cache import citation_path
        cites = _scan()
        rep = next(c for c in cites if c.is_repeat)
        assert citation_path(rep) is None


class TestRepeatParallels:
    TEXT = (
        "First cite: Olson v. Estate of Olson, 2024 ND 156, ¶ 7, 10 N.W.3d "
        "500. Some intervening discussion. Restated in full: Olson v. Estate "
        "of Olson, 2024 ND 156, ¶ 14, 10 N.W.3d 500."
    )

    def test_restated_parallel_pair_linked(self):
        cites = _scan(self.TEXT)
        rep_neutral = next(c for c in cites
                           if c.is_repeat and c.normalized == "2024 ND 156")
        assert "10 N.W.3d 500" in rep_neutral.parallel_cites

    def test_primary_parallels_unaffected(self):
        cites = _scan(self.TEXT)
        primary = next(c for c in cites
                       if c.normalized == "2024 ND 156" and not c.is_repeat)
        assert primary.parallel_cites == ["10 N.W.3d 500"]


class TestLegacyDict:
    def test_position_emitted(self, tmp_path):
        cites = _scan()
        entries = [to_legacy_dict(c, tmp_path) for c in cites]
        assert all(isinstance(e["position"], int) for e in entries)

    def test_repeat_entry_fields(self, tmp_path):
        cites = _scan()
        rep = next(c for c in cites if c.is_repeat and c.pinpoint == "¶ 12")
        entry = to_legacy_dict(rep, tmp_path)
        assert entry["is_repeat"] is True
        assert entry["parent_normalized"] == "2024 ND 156"
        assert entry["local_path"] is None
        assert entry["cite_type"] == "neutral_cite"

    def test_add_parallel_info_repeat_safe(self, tmp_path):
        cites = _scan(TestRepeatParallels.TEXT)
        entries = [to_legacy_dict(c, tmp_path) for c in cites]
        add_parallel_info(entries, cites)
        rep_entry = next(e for e in entries if e.get("is_repeat")
                         and e["normalized"] == "2024 ND 156")
        assert rep_entry["parallel_cite"] == "10 N.W.3d 500"
        assert "preferred" not in rep_entry

    def test_to_dict_emits_is_repeat(self):
        cites = _scan()
        rep = next(c for c in cites if c.is_repeat)
        d = rep.to_dict()
        assert d["is_repeat"] is True
        assert d["parent_normalized"] == rep.parent_normalized


# ---------------------------------------------------------------------------
# Non-case repeats: statutes, court rules, constitutions
# ---------------------------------------------------------------------------

PROVISIONS = (
    "[¶1] The motion did not invoke N.D.R.Ev. 702. At the hearing, counsel "
    "said nothing further. "
    "[¶2] The appellee argues no objection rested on N.D.R.Ev. 702, so "
    "the issue is forfeited. "
    "[¶3] Under N.D.R.Ev. 702(b), an expert may testify. Under "
    "N.D.R.Ev. 702(c), the testimony must rest on sufficient facts. Id. "
    "[¶4] Rule 702(c), N.D.R.Ev., does not authorize it. "
    "[¶5] See N.D.R.Civ.P. 56(b). Also N.D.R.Civ.P. 56(a) and "
    "N.D.R.Ev. 901(a). "
    "[¶6] N.D.C.C. § 28-01-16(1)(a) applies. So does "
    "N.D.C.C. § 28-01-16(2). N.D. Const. art. VI, § 2 controls. "
    "Again, N.D. Const. art. VI, § 2."
)


def _fulls_of(cites, normalized):
    return [c for c in cites if c.normalized == normalized and not c.is_pin_cite]


class TestProvisionRepeats:
    def test_every_rule_occurrence_emitted(self):
        cites = _scan(PROVISIONS, include_pin_cites=True)
        ev702 = _fulls_of(cites, "N.D.R.Ev. 702")
        # ¶1, ¶2, 702(b), 702(c), and the suffix-form "Rule 702(c), N.D.R.Ev."
        assert len(ev702) == 5
        assert [c.is_repeat for c in ev702] == [False, True, True, True, True]
        assert all(c.parent_normalized == "N.D.R.Ev. 702" for c in ev702[1:])
        assert [c.pinpoint for c in ev702] == [None, None, "(b)", "(c)", "(c)"]

    def test_repeat_links_to_first_occurrence_position(self):
        cites = _scan(PROVISIONS)
        ev702 = _fulls_of(cites, "N.D.R.Ev. 702")
        first = ev702[0]
        for rep in ev702[1:]:
            assert rep.components["parent_position"] == first.position
            assert rep.position > first.position

    def test_different_subdivision_is_repeat_not_new_authority(self):
        cites = _scan(PROVISIONS)
        crim52 = _fulls_of(cites, "N.D.R.Civ.P. 56")
        assert [(c.is_repeat, c.pinpoint) for c in crim52] == [
            (False, "(b)"), (True, "(a)")]
        assert not any(c.normalized.startswith("N.D.R.Civ.P. 56(")
                       for c in cites)

    def test_statute_subsections_each_occurrence(self):
        cites = _scan(PROVISIONS)
        stat = _fulls_of(cites, "N.D.C.C. § 28-01-16")
        assert [(c.is_repeat, c.pinpoint) for c in stat] == [
            (False, "(1)(a)"), (True, "(2)")]
        assert stat[0].components["subsection"] == "(1)(a)"
        assert stat[0].raw_text.startswith("N.D.C.C. § 28-01-16(1)(a)")

    def test_constitution_repeat_emitted(self):
        cites = _scan(PROVISIONS)
        const = _fulls_of(cites, "N.D. Const. art. VI, § 2")
        assert [c.is_repeat for c in const] == [False, True]
        assert const[1].parent_normalized == "N.D. Const. art. VI, § 2"

    def test_bare_id_inherits_subdivision(self):
        cites = _scan(PROVISIONS, include_pin_cites=True)
        ids = [c for c in cites if c.is_pin_cite and c.raw_text.startswith("Id")]
        assert len(ids) == 1
        assert ids[0].parent_normalized == "N.D.R.Ev. 702"
        assert ids[0].pinpoint == "(c)"
        assert ids[0].components["pinpoint_inherited"] is True

    def test_repeat_inherits_parent_sources(self):
        cites = _scan(PROVISIONS)
        ev702 = _fulls_of(cites, "N.D.R.Ev. 702")
        assert ev702[0].sources
        for rep in ev702[1:]:
            assert [s.url for s in rep.sources] == [s.url for s in ev702[0].sources]

    def test_default_mode_unchanged_for_provisions(self):
        cites = scan_text(PROVISIONS, resolve=False, include_pin_cites=True)
        assert not any(c.is_repeat for c in cites)
        norms = [c.normalized for c in cites if not c.is_pin_cite]
        assert norms.count("N.D.R.Ev. 702") == 1
        assert norms.count("N.D.C.C. § 28-01-16") == 1
        assert norms.count("N.D. Const. art. VI, § 2") == 1
        # The re-cited rule still anchors the following Id. (shadow path).
        ids = [c for c in cites if c.is_pin_cite and c.raw_text.startswith("Id")]
        assert ids[0].parent_normalized == "N.D.R.Ev. 702"

    def test_positions_sorted(self):
        cites = _scan(PROVISIONS, include_pin_cites=True)
        positions = [c.position for c in cites]
        assert positions == sorted(positions)

    def test_legacy_dict_repeat_fields(self, tmp_path):
        cites = _scan(PROVISIONS)
        rep = _fulls_of(cites, "N.D.R.Ev. 702")[2]
        d = to_legacy_dict(rep, tmp_path)
        assert d["is_repeat"] is True
        assert d["parent_normalized"] == "N.D.R.Ev. 702"
        assert d["pinpoint"] == "(b)"
        assert d["cite_text"] == "N.D.R.Ev. 702(b)"
