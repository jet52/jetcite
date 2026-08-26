"""A cached file must not launder an asserted pairing into a confirmation.

Scanning "State v. X, 2025 ND 228, 29 N.W.3d 885" links the two cites and
merges their source lists, which is what makes the bare reporter cite
fetchable at all -- it has no resolver of its own. But the URL that reaches
the opinion was built from the *neutral* cite, so the fetch succeeds only
because this document paired them. Cached at the reporter's path with no
record of that, the next run finds an existing file for "29 N.W.3d 885" and
reads it as independent verification of a pairing nobody checked.

Observed in the wild: ~/refs/opin/NW3d/29/885.md carries
source_url=".../opinions?cit1=2025&citType=ND&cit2=228" -- a search for the
neutral cite, stored under the reporter's volume and page.
"""

import json

import pytest

from jetcite.cache import cache_content, source_trust
from jetcite.models import Citation, CitationType, Source
from jetcite.scanner import scan_text


def neutral_and_parallel(text="State v. X, 2025 ND 228, 29 N.W.3d 885 (N.D. 2025)."):
    cites = [c for c in scan_text(text) if c.cite_type == CitationType.CASE
             and not c.is_pin_cite and not c.is_repeat]
    by_norm = {c.normalized: c for c in cites}
    return by_norm


def test_merged_source_records_the_cite_it_actually_addresses():
    by_norm = neutral_and_parallel()
    reporter = by_norm.get("29 N.W.3d 885")
    assert reporter is not None, f"scanner produced {list(by_norm)}"
    merged = [s for s in reporter.sources if s.via_parallel]
    assert merged, "the reporter cite's inherited sources must be stamped"
    assert all(s.via_parallel == "2025 ND 228" for s in merged)


def test_a_citations_own_source_is_not_stamped():
    """Only merged sources carry via_parallel; the neutral cite's own
    ndcourts URL addresses the neutral cite and must stay unstamped."""
    by_norm = neutral_and_parallel()
    neutral = by_norm["2025 ND 228"]
    own = [s for s in neutral.sources if not s.via_parallel]
    assert own, "the neutral cite must keep at least one source of its own"


def cite(normalized="29 N.W.3d 885", **over):
    c = Citation(
        raw_text=normalized, cite_type=CitationType.CASE, jurisdiction="us",
        normalized=normalized,
        components={"reporter": "N.W.3d", "volume": "29", "page": "885"},
    )
    for k, v in over.items():
        setattr(c, k, v)
    return c


def test_pairing_is_recorded_and_refuses_to_confirm(tmp_path):
    path = cache_content(cite(), "opinion text", tmp_path,
                         source_url="https://www.ndcourts.gov/supreme-court/"
                                    "opinions?cit1=2025&citType=ND&cit2=228",
                         via_parallel="2025 ND 228")
    assert path is not None
    meta = json.loads(path.with_suffix(path.suffix + ".meta.json")
                      .read_text(encoding="utf-8"))
    assert meta["pairing"] == {"resolved_from": "2025 ND 228",
                               "basis": "asserted-by-source"}
    trust = source_trust(path)
    assert trust["pairing_basis"] == "asserted-by-source"
    assert trust["confirms"] is False


def test_an_independently_resolved_fetch_does_confirm(tmp_path):
    path = cache_content(cite(), "opinion text", tmp_path,
                         source_url="https://www.courtlistener.com/opinion/1/x/")
    trust = source_trust(path)
    assert trust["origin"] == "web-fetch"
    assert trust["pairing_basis"] is None
    assert trust["confirms"] is True


def test_corpus_origin_is_recorded(tmp_path):
    path = cache_content(cite(), "opinion text", tmp_path,
                         source_url="https://www.ndcourts.gov/supreme-court/opinions/1",
                         origin="ndlaw-corpus")
    assert source_trust(path)["origin"] == "ndlaw-corpus"


def test_a_file_cached_before_this_policy_confirms_nothing(tmp_path):
    """Every file already on disk was written without these keys. Silence is
    not evidence, so an old sidecar reads as unknown and confirms nothing."""
    path = cache_content(cite(), "opinion text", tmp_path,
                         source_url="https://example.gov/x")
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    del meta["origin"]
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    trust = source_trust(path)
    assert trust["origin"] == "unknown"
    assert trust["confirms"] is False


def test_the_legacy_via_ndlaw_key_still_reads_as_corpus(tmp_path):
    """ndlaw_export stamped `via` before `origin` existed; 21 such files are
    already on disk here."""
    path = cache_content(cite(), "opinion text", tmp_path,
                         source_url="https://www.ndcourts.gov/x")
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    del meta["origin"]
    meta["via"] = "ndlaw"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    assert source_trust(path)["origin"] == "ndlaw-corpus"


def test_source_trust_on_a_file_with_no_sidecar(tmp_path):
    orphan = tmp_path / "orphan.md"
    orphan.write_text("text", encoding="utf-8")
    trust = source_trust(orphan)
    assert trust["origin"] == "unknown" and trust["confirms"] is False
