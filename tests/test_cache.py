"""Tests for the local reference cache module.

All tests use pytest's tmp_path fixture — nothing touches ~/refs/.
"""

import json
from pathlib import Path

import pytest

from jetcite.cache import (
    add_local_source,
    cache_content,
    is_stale,
    read_meta,
    resolve_local,
)
from jetcite.models import Citation, CitationType, Source


# ── Helpers ──────────────────────────────────────────────────────


def _nd_opinion() -> Citation:
    return Citation(
        raw_text="2024 ND 156",
        cite_type=CitationType.CASE,
        jurisdiction="nd",
        normalized="2024 ND 156",
        components={"year": "2024", "number": "156"},
        sources=[Source("ndcourts", "https://www.ndcourts.gov/supreme-court/opinion/2024ND156")],
    )


def _usc_cite() -> Citation:
    return Citation(
        raw_text="42 U.S.C. § 1983",
        cite_type=CitationType.STATUTE,
        jurisdiction="us",
        normalized="42 U.S.C. § 1983",
        components={"title": "42", "section": "1983"},
        sources=[Source("govinfo", "https://www.govinfo.gov/...")],
    )


def _ndcc_cite() -> Citation:
    return Citation(
        raw_text="N.D.C.C. § 12.1-32-01",
        cite_type=CitationType.STATUTE,
        jurisdiction="nd",
        normalized="N.D.C.C. § 12.1-32-01",
        components={"title": "12.1", "chapter": "32", "section": "01"},
        sources=[Source("ndlegis", "https://ndlegis.gov/...")],
    )


def _federal_case() -> Citation:
    return Citation(
        raw_text="505 U.S. 377",
        cite_type=CitationType.CASE,
        jurisdiction="us",
        normalized="505 U.S. 377",
        components={"volume": "505", "reporter": "U.S.", "page": "377"},
        sources=[Source("justia", "https://supreme.justia.com/cases/federal/us/505/377/")],
    )


def _nd_const() -> Citation:
    return Citation(
        raw_text="N.D. Const. art. I, § 20",
        cite_type=CitationType.CONSTITUTION,
        jurisdiction="nd",
        normalized="N.D. Const. art. I, § 20",
        components={"article": "I", "section": "20"},
        sources=[Source("ndconst", "https://ndconst.org/arti/sec20/")],
    )


def _nd_court_rule() -> Citation:
    return Citation(
        raw_text="N.D.R.Civ.P. 56",
        cite_type=CitationType.COURT_RULE,
        jurisdiction="nd",
        normalized="N.D.R.Civ.P. 56",
        components={"rule_set": "civil-procedure", "rule_number": "56"},
        sources=[Source("ndcourts", "https://www.ndcourts.gov/...")],
    )


def _ndac_cite() -> Citation:
    return Citation(
        raw_text="N.D.A.C. § 43-02-05-01",
        cite_type=CitationType.REGULATION,
        jurisdiction="nd",
        normalized="N.D.A.C. § 43-02-05-01",
        components={"p1": "43", "p2": "02", "p3": "05", "p4": "01"},
        sources=[Source("ndlegis", "https://ndlegis.gov/...")],
    )


# ── resolve_local ───────────────────────────────────────────────


def test_resolve_local_not_cached(tmp_path):
    assert resolve_local(_nd_opinion(), tmp_path) is None


def test_resolve_local_found(tmp_path):
    cite = _nd_opinion()
    # Manually create the expected file
    path = tmp_path / "opin/markdown/2024/2024ND156.md"
    path.parent.mkdir(parents=True)
    path.write_text("# 2024 ND 156\nOpinion text here.")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_federal_case(tmp_path):
    cite = _federal_case()
    path = tmp_path / "federal/opinions/US/505/377.md"
    path.parent.mkdir(parents=True)
    path.write_text("opinion")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_usc(tmp_path):
    cite = _usc_cite()
    path = tmp_path / "federal/usc/42/1983.md"
    path.parent.mkdir(parents=True)
    path.write_text("statute")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_ndcc(tmp_path):
    cite = _ndcc_cite()
    path = tmp_path / "ndcc/title-12.1/chapter-12.1-32.md"
    path.parent.mkdir(parents=True)
    path.write_text("chapter")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_nd_const(tmp_path):
    cite = _nd_const()
    path = tmp_path / "cnst/art-I/sec-20.md"
    path.parent.mkdir(parents=True)
    path.write_text("section")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_court_rule(tmp_path):
    cite = _nd_court_rule()
    path = tmp_path / "rule/civil-procedure/rule-56.md"
    path.parent.mkdir(parents=True)
    path.write_text("rule")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_ndac(tmp_path):
    cite = _ndac_cite()
    path = tmp_path / "ndac/title-43/article-43-02/chapter-43-02-05.md"
    path.parent.mkdir(parents=True)
    path.write_text("admin rule")
    assert resolve_local(cite, tmp_path) == path


# ── cache_content ───────────────────────────────────────────────


def test_cache_content_creates_file(tmp_path):
    cite = _nd_opinion()
    content = "# 2024 ND 156\n\nOpinion text."
    path = cache_content(cite, content, tmp_path)
    assert path is not None
    assert path.is_file()
    assert path.read_text() == content


def test_cache_content_creates_meta(tmp_path):
    cite = _nd_opinion()
    path = cache_content(cite, "content", tmp_path, source_url="https://example.com")
    meta_path = path.with_suffix(".md.meta.json")
    assert meta_path.is_file()
    meta = json.loads(meta_path.read_text())
    assert meta["citation"] == "2024 ND 156"
    assert meta["source_url"] == "https://example.com"
    assert "fetched" in meta


def test_cache_content_uses_primary_url(tmp_path):
    cite = _nd_opinion()
    path = cache_content(cite, "content", tmp_path)
    meta = read_meta(path)
    assert meta["source_url"] == cite.sources[0].url


def test_cache_content_creates_dirs(tmp_path):
    cite = _federal_case()
    path = cache_content(cite, "opinion text", tmp_path)
    assert path is not None
    assert path.parent.is_dir()


def test_cache_roundtrip(tmp_path):
    """Cache content, then resolve it."""
    cite = _nd_opinion()
    cache_content(cite, "cached opinion", tmp_path)
    found = resolve_local(cite, tmp_path)
    assert found is not None
    assert found.read_text() == "cached opinion"


# ── read_meta ───────────────────────────────────────────────────


def test_read_meta_missing(tmp_path):
    assert read_meta(tmp_path / "nonexistent.md") is None


def test_read_meta_exists(tmp_path):
    cite = _nd_opinion()
    path = cache_content(cite, "content", tmp_path)
    meta = read_meta(path)
    assert meta is not None
    assert meta["citation"] == "2024 ND 156"


# ── is_stale ────────────────────────────────────────────────────


def test_stale_case_permanent(tmp_path):
    """Case citations (opinions) should never be stale."""
    cite = _nd_opinion()
    path = cache_content(cite, "content", tmp_path)
    assert is_stale(cite, path) is False


def test_stale_statute_fresh(tmp_path):
    """A just-cached statute should not be stale."""
    cite = _usc_cite()
    path = cache_content(cite, "content", tmp_path)
    assert is_stale(cite, path) is False


def test_stale_statute_old(tmp_path):
    """A statute cached > 90 days ago should be stale."""
    cite = _usc_cite()
    path = cache_content(cite, "content", tmp_path)
    # Backdate the metadata
    meta = read_meta(path)
    meta["fetched"] = "2025-01-01T00:00:00+00:00"
    meta_path = path.with_suffix(".md.meta.json")
    meta_path.write_text(json.dumps(meta))
    assert is_stale(cite, path) is True


def test_stale_no_meta(tmp_path):
    """No metadata means we can't determine staleness."""
    path = tmp_path / "test.md"
    path.write_text("content")
    cite = _usc_cite()
    assert is_stale(cite, path) is None


# ── add_local_source ────────────────────────────────────────────


def test_add_local_source(tmp_path):
    cite = _nd_opinion()
    path = tmp_path / "test.md"
    path.write_text("content")
    add_local_source(cite, path)
    assert cite.sources[0].name == "local"
    assert cite.sources[0].url.startswith("file://")


def test_add_local_source_no_duplicate(tmp_path):
    cite = _nd_opinion()
    path = tmp_path / "test.md"
    path.write_text("content")
    add_local_source(cite, path)
    add_local_source(cite, path)
    local_sources = [s for s in cite.sources if s.name == "local"]
    assert len(local_sources) == 1
