"""Tests for the local reference cache module.

All tests use pytest's tmp_path fixture — nothing touches ~/refs/.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from jetcite.cache import (
    _citation_path,
    _reporter_dir,
    _ND_REPORTERS,
    _FEDERAL_REPORTERS,
    add_local_source,
    cache_content,
    fetch_and_cache,
    is_stale,
    read_meta,
    resolve_local,
)
from jetcite.models import Citation, CitationType, Source
from jetcite.scanner import lookup, scan_text


# ── Helpers ──────────────────────────────────────────────────────


def _nd_opinion() -> Citation:
    return Citation(
        raw_text="2024 ND 156",
        cite_type=CitationType.CASE,
        jurisdiction="nd",
        normalized="2024 ND 156",
        components={"year": "2024", "number": "156"},
        sources=[Source("ndcourts", "https://www.ndcourts.gov/supreme-court/opinions/171302")],
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
        components={"rule_set": "civil-procedure", "parts": ["56"]},
        sources=[Source("ndcourts", "https://www.ndcourts.gov/...")],
    )


def _ndac_cite() -> Citation:
    return Citation(
        raw_text="N.D.A.C. § 43-02-05-01",
        cite_type=CitationType.REGULATION,
        jurisdiction="nd",
        normalized="N.D.A.C. § 43-02-05-01",
        components={"part1": "43", "part2": "02", "part3": "05", "part4": "01"},
        sources=[Source("ndlegis", "https://ndlegis.gov/...")],
    )


# ── _reporter_dir ─────────────────────────────────────────────


def test_reporter_dir_us():
    assert _reporter_dir("U.S.") == "scotus"


def test_reporter_dir_strips_periods_spaces():
    assert _reporter_dir("F. Supp. 3d") == "FSupp3d"
    assert _reporter_dir("S. Ct.") == "SCt"
    assert _reporter_dir("N.W.2d") == "NW2d"
    assert _reporter_dir("L. Ed. 2d") == "LEd2d"


def test_reporter_dir_strips_apostrophes():
    assert _reporter_dir("F. App'x") == "FAppx"
    assert _reporter_dir("F. App\u2019x") == "FAppx"


# ── _citation_path: three-tier case routing ──────────────────


def test_path_nd_neutral():
    p = _citation_path(_nd_opinion())
    assert p == Path("nd/opin/markdown/2024/2024ND156.md")


def test_path_nd_reporter_nw2d():
    cite = Citation(
        raw_text="355 N.W.2d 16",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="355 N.W.2d 16",
        components={"volume": "355", "reporter": "N.W.2d", "page": "16"},
    )
    assert _citation_path(cite) == Path("nd/opin/NW2d/355/16.md")


def test_path_nd_reporter_nw():
    cite = Citation(
        raw_text="1 N.W. 100",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="1 N.W. 100",
        components={"volume": "1", "reporter": "N.W.", "page": "100"},
    )
    assert _citation_path(cite) == Path("nd/opin/NW/1/100.md")


def test_path_nd_reporter_nd():
    cite = Citation(
        raw_text="50 N.D. 123",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="50 N.D. 123",
        components={"volume": "50", "reporter": "N.D.", "page": "123"},
    )
    assert _citation_path(cite) == Path("nd/opin/ND/50/123.md")


def test_path_federal_scotus():
    assert _citation_path(_federal_case()) == Path("us/scotus/505/377.md")


def test_path_federal_f3d():
    cite = Citation(
        raw_text="500 F.3d 200",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="500 F.3d 200",
        components={"volume": "500", "reporter": "F.3d", "page": "200"},
    )
    assert _citation_path(cite) == Path("us/F3d/500/200.md")


def test_path_federal_sct():
    cite = Citation(
        raw_text="140 S. Ct. 1731",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="140 S. Ct. 1731",
        components={"volume": "140", "reporter": "S. Ct.", "page": "1731"},
    )
    assert _citation_path(cite) == Path("us/SCt/140/1731.md")


def test_path_federal_fsupp3d():
    cite = Citation(
        raw_text="300 F. Supp. 3d 100",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="300 F. Supp. 3d 100",
        components={"volume": "300", "reporter": "F. Supp. 3d", "page": "100"},
    )
    assert _citation_path(cite) == Path("us/FSupp3d/300/100.md")


def test_path_reporter_nw3d():
    """N.W.3d goes to reporter/ (not opin/) since ND uses neutral cites."""
    cite = Citation(
        raw_text="10 N.W.3d 500",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="10 N.W.3d 500",
        components={"volume": "10", "reporter": "N.W.3d", "page": "500"},
    )
    assert _citation_path(cite) == Path("reporter/NW3d/10/500.md")


def test_path_reporter_p2d():
    cite = Citation(
        raw_text="800 P.2d 500",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="800 P.2d 500",
        components={"volume": "800", "reporter": "P.2d", "page": "500"},
    )
    assert _citation_path(cite) == Path("reporter/P2d/800/500.md")


def test_path_reporter_a3d():
    cite = Citation(
        raw_text="200 A.3d 100",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="200 A.3d 100",
        components={"volume": "200", "reporter": "A.3d", "page": "100"},
    )
    assert _citation_path(cite) == Path("reporter/A3d/200/100.md")


# ── _citation_path: non-case types ──────────────────────────


def test_path_usc():
    assert _citation_path(_usc_cite()) == Path("us/usc/42/1983.md")


def test_path_ndcc():
    assert _citation_path(_ndcc_cite()) == Path("nd/code/title-12.1/chapter-12.1-32.md")


def test_path_nd_const():
    assert _citation_path(_nd_const()) == Path("nd/cnst/art-01/sec-20.md")


def test_path_ndac():
    assert _citation_path(_ndac_cite()) == Path("nd/regs/title-43/article-43-02/chapter-43-02-05.md")


def test_path_cfr():
    cite = Citation(
        raw_text="29 C.F.R. § 1630.2",
        cite_type=CitationType.REGULATION, jurisdiction="us",
        normalized="29 C.F.R. § 1630.2",
        components={"title": "29", "section": "1630.2"},
    )
    assert _citation_path(cite) == Path("us/cfr/29/1630.2.md")


def test_path_court_rule():
    assert _citation_path(_nd_court_rule()) == Path("nd/rule/civil-procedure/rule-56.md")


def test_path_unknown_returns_none():
    cite = Citation(
        raw_text="unknown", cite_type=CitationType.CASE,
        jurisdiction="us", normalized="unknown", components={},
    )
    assert _citation_path(cite) is None


# ── resolve_local ───────────────────────────────────────────────


def test_resolve_local_not_cached(tmp_path):
    assert resolve_local(_nd_opinion(), tmp_path) is None


def test_resolve_local_found(tmp_path):
    cite = _nd_opinion()
    path = tmp_path / "nd/opin/markdown/2024/2024ND156.md"
    path.parent.mkdir(parents=True)
    path.write_text("# 2024 ND 156\nOpinion text here.")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_federal_case(tmp_path):
    cite = _federal_case()
    path = tmp_path / "us/scotus/505/377.md"
    path.parent.mkdir(parents=True)
    path.write_text("opinion")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_usc(tmp_path):
    cite = _usc_cite()
    path = tmp_path / "us/usc/42/1983.md"
    path.parent.mkdir(parents=True)
    path.write_text("statute")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_ndcc(tmp_path):
    cite = _ndcc_cite()
    path = tmp_path / "nd/code/title-12.1/chapter-12.1-32.md"
    path.parent.mkdir(parents=True)
    path.write_text("chapter")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_nd_const(tmp_path):
    cite = _nd_const()
    path = tmp_path / "nd/cnst/art-01/sec-20.md"
    path.parent.mkdir(parents=True)
    path.write_text("section")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_court_rule(tmp_path):
    cite = _nd_court_rule()
    path = tmp_path / "nd/rule/civil-procedure/rule-56.md"
    path.parent.mkdir(parents=True)
    path.write_text("rule")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_ndac(tmp_path):
    cite = _ndac_cite()
    path = tmp_path / "nd/regs/title-43/article-43-02/chapter-43-02-05.md"
    path.parent.mkdir(parents=True)
    path.write_text("admin rule")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_nd_reporter(tmp_path):
    """N.W.2d case resolves under nd/opin/."""
    cite = Citation(
        raw_text="355 N.W.2d 16",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="355 N.W.2d 16",
        components={"volume": "355", "reporter": "N.W.2d", "page": "16"},
    )
    path = tmp_path / "nd/opin/NW2d/355/16.md"
    path.parent.mkdir(parents=True)
    path.write_text("opinion")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_state_reporter(tmp_path):
    """P.2d case resolves under reporter/."""
    cite = Citation(
        raw_text="800 P.2d 500",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="800 P.2d 500",
        components={"volume": "800", "reporter": "P.2d", "page": "500"},
    )
    path = tmp_path / "reporter/P2d/800/500.md"
    path.parent.mkdir(parents=True)
    path.write_text("opinion")
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


def test_stale_constitution_permanent(tmp_path):
    """Constitution citations should never be stale."""
    cite = _nd_const()
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
    meta = read_meta(path)
    meta["fetched"] = "2025-01-01T00:00:00+00:00"
    meta_path = path.with_suffix(".md.meta.json")
    meta_path.write_text(json.dumps(meta))
    assert is_stale(cite, path) is True


def test_stale_court_rule_fresh(tmp_path):
    """A just-cached court rule should not be stale."""
    cite = _nd_court_rule()
    path = cache_content(cite, "content", tmp_path)
    assert is_stale(cite, path) is False


def test_stale_court_rule_old(tmp_path):
    """A court rule cached > 180 days ago should be stale."""
    cite = _nd_court_rule()
    path = cache_content(cite, "content", tmp_path)
    meta = read_meta(path)
    meta["fetched"] = "2025-01-01T00:00:00+00:00"
    meta_path = path.with_suffix(".md.meta.json")
    meta_path.write_text(json.dumps(meta))
    assert is_stale(cite, path) is True


def test_stale_regulation_fresh(tmp_path):
    """A just-cached regulation should not be stale."""
    cite = _ndac_cite()
    path = cache_content(cite, "content", tmp_path)
    assert is_stale(cite, path) is False


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


# ── fetch_and_cache ────────────────────────────────────────────


def test_fetch_and_cache_downloads(tmp_path):
    """fetch_and_cache should download content and write to cache."""
    cite = _nd_opinion()

    mock_resp = MagicMock()
    mock_resp.text = "<h1>2024 ND 156</h1><p>Fetched opinion.</p>"
    mock_resp.headers = {"content-type": "text/html; charset=utf-8"}
    mock_resp.raise_for_status = MagicMock()

    with patch("jetcite.cache.httpx.get", return_value=mock_resp) as mock_get:
        path = fetch_and_cache(cite, refs_dir=tmp_path)

    assert path is not None
    assert path.is_file()
    # HTML should be converted to markdown
    content = path.read_text()
    assert "2024 ND 156" in content
    assert "<h1>" not in content
    mock_get.assert_called_once()

    # Should have added a local source
    assert cite.sources[0].name == "local"


def test_fetch_and_cache_skips_if_cached(tmp_path):
    """fetch_and_cache should not re-download if already cached."""
    cite = _nd_opinion()
    cache_content(cite, "already cached", tmp_path)

    with patch("jetcite.cache.httpx.get") as mock_get:
        path = fetch_and_cache(cite, refs_dir=tmp_path)

    assert path is not None
    assert path.read_text() == "already cached"
    mock_get.assert_not_called()


def test_fetch_and_cache_http_error(tmp_path):
    """fetch_and_cache should return None on HTTP error."""
    import httpx
    cite = _nd_opinion()

    with patch("jetcite.cache.httpx.get", side_effect=httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock())):
        path = fetch_and_cache(cite, refs_dir=tmp_path)

    assert path is None


def test_fetch_and_cache_no_sources(tmp_path):
    """fetch_and_cache should return None if citation has no web sources."""
    cite = Citation(
        raw_text="unknown",
        cite_type=CitationType.CASE,
        jurisdiction="us",
        normalized="unknown",
        components={},
        sources=[],
    )
    path = fetch_and_cache(cite, refs_dir=tmp_path)
    assert path is None


# ── lookup/scan_text with refs_dir ─────────────────────────────


def test_lookup_with_refs_dir(tmp_path):
    """lookup() with refs_dir adds local source when cached."""
    # Pre-cache a known citation
    cached_path = tmp_path / "nd/opin/markdown/2024/2024ND156.md"
    cached_path.parent.mkdir(parents=True)
    cached_path.write_text("cached opinion")

    result = lookup("2024 ND 156", refs_dir=tmp_path)
    assert result is not None
    assert result.sources[0].name == "local"
    assert result.sources[0].url.startswith("file://")


def test_lookup_without_refs_dir():
    """lookup() without refs_dir should work as before (no local source)."""
    result = lookup("2024 ND 156")
    assert result is not None
    assert all(s.name != "local" for s in result.sources)


def test_scan_text_with_refs_dir(tmp_path):
    """scan_text() with refs_dir adds local sources for cached citations."""
    # Pre-cache
    cached_path = tmp_path / "nd/opin/markdown/2024/2024ND156.md"
    cached_path.parent.mkdir(parents=True)
    cached_path.write_text("cached opinion")

    text = "The court decided in 2024 ND 156 that the statute was valid."
    results = scan_text(text, refs_dir=tmp_path)
    nd_cite = [c for c in results if c.normalized == "2024 ND 156"]
    assert len(nd_cite) == 1
    assert nd_cite[0].sources[0].name == "local"


def test_scan_text_refs_dir_miss(tmp_path):
    """scan_text() with refs_dir but no cached file — no local source."""
    text = "The court decided in 2024 ND 156 that the statute was valid."
    results = scan_text(text, refs_dir=tmp_path)
    nd_cite = [c for c in results if c.normalized == "2024 ND 156"]
    assert len(nd_cite) == 1
    assert all(s.name != "local" for s in nd_cite[0].sources)
