"""Tests for the local reference cache module.

All tests use pytest's tmp_path fixture — nothing touches ~/refs/.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from jetcite.cache import (
    _citation_path,
    _FEDERAL_RULE_DIRS,
    _reporter_dir,
    _ND_REPORTERS,
    _FEDERAL_REPORTERS,
    add_local_source,
    cache_content,
    citation_path,
    fetch_and_cache,
    is_stale,
    read_meta,
    resolve_local,
    write_meta,
)
from jetcite.models import Citation, CitationType, Source
from jetcite.scanner import lookup, scan_text


# ── Helpers ──────────────────────────────────────────────────────


def _nd_opinion() -> Citation:
    """Test helper — uses a generic URL so fetch tests hit _fetch_generic."""
    return Citation(
        raw_text="2024 ND 156",
        cite_type=CitationType.CASE,
        jurisdiction="nd",
        normalized="2024 ND 156",
        components={"year": "2024", "number": "156"},
        sources=[Source("ndcourts", "https://example.com/opinions/2024ND156")],
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
        components={"rule_set": "ndrcivp", "parts": ["56"]},
        sources=[Source("ndcourts", "https://www.ndcourts.gov/...")],
    )


def _federal_rule() -> Citation:
    return Citation(
        raw_text="Fed. R. Civ. P. 12(b)(6)",
        cite_type=CitationType.COURT_RULE,
        jurisdiction="us",
        normalized="Fed. R. Civ. P. 12(b)(6)",
        components={"rule_set": "frcp", "rule_number": "12", "subsection": "(b)(6)"},
        sources=[Source("cornell", "https://www.law.cornell.edu/rules/frcivp/rule_12")],
    )


def _us_const_amend() -> Citation:
    return Citation(
        raw_text="U.S. Const. amend. XIV",
        cite_type=CitationType.CONSTITUTION,
        jurisdiction="us",
        normalized="U.S. Const. amend. XIV",
        components={"amendment": "XIV"},
        sources=[Source("constitutioncenter", "https://constitutioncenter.org/...")],
    )


def _us_const_article() -> Citation:
    return Citation(
        raw_text="U.S. Const. art. III, § 2",
        cite_type=CitationType.CONSTITUTION,
        jurisdiction="us",
        normalized="U.S. Const. art. III, § 2",
        components={"article": "III", "section": "2"},
        sources=[Source("constitutioncenter", "https://constitutioncenter.org/...")],
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
    assert _reporter_dir("U.S.") == "US"


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
    assert p == Path("opin/ND/2024/2024ND156.md")


def test_path_nd_reporter_nw2d():
    cite = Citation(
        raw_text="355 N.W.2d 16",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="355 N.W.2d 16",
        components={"volume": "355", "reporter": "N.W.2d", "page": "16"},
    )
    assert _citation_path(cite) == Path("opin/NW2d/355/16.md")


def test_path_nd_reporter_nw():
    cite = Citation(
        raw_text="1 N.W. 100",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="1 N.W. 100",
        components={"volume": "1", "reporter": "N.W.", "page": "100"},
    )
    assert _citation_path(cite) == Path("opin/NW/1/100.md")


def test_path_nd_reporter_nd():
    cite = Citation(
        raw_text="50 N.D. 123",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="50 N.D. 123",
        components={"volume": "50", "reporter": "N.D.", "page": "123"},
    )
    assert _citation_path(cite) == Path("opin/ND/50/123.md")


def test_path_federal_scotus():
    assert _citation_path(_federal_case()) == Path("opin/US/505/377.md")


def test_path_federal_f3d():
    cite = Citation(
        raw_text="500 F.3d 200",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="500 F.3d 200",
        components={"volume": "500", "reporter": "F.3d", "page": "200"},
    )
    assert _citation_path(cite) == Path("opin/F3d/500/200.md")


def test_path_federal_sct():
    cite = Citation(
        raw_text="140 S. Ct. 1731",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="140 S. Ct. 1731",
        components={"volume": "140", "reporter": "S. Ct.", "page": "1731"},
    )
    assert _citation_path(cite) == Path("opin/SCt/140/1731.md")


def test_path_federal_fsupp3d():
    cite = Citation(
        raw_text="300 F. Supp. 3d 100",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="300 F. Supp. 3d 100",
        components={"volume": "300", "reporter": "F. Supp. 3d", "page": "100"},
    )
    assert _citation_path(cite) == Path("opin/FSupp3d/300/100.md")


def test_path_reporter_nw3d():
    """All reporters go under opin/{reporter}/ — no special routing."""
    cite = Citation(
        raw_text="10 N.W.3d 500",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="10 N.W.3d 500",
        components={"volume": "10", "reporter": "N.W.3d", "page": "500"},
    )
    assert _citation_path(cite) == Path("opin/NW3d/10/500.md")


def test_path_reporter_p2d():
    cite = Citation(
        raw_text="800 P.2d 500",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="800 P.2d 500",
        components={"volume": "800", "reporter": "P.2d", "page": "500"},
    )
    assert _citation_path(cite) == Path("opin/P2d/800/500.md")


def test_path_reporter_a3d():
    cite = Citation(
        raw_text="200 A.3d 100",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="200 A.3d 100",
        components={"volume": "200", "reporter": "A.3d", "page": "100"},
    )
    assert _citation_path(cite) == Path("opin/A3d/200/100.md")


# ── _citation_path: non-case types ──────────────────────────


def test_path_usc():
    assert _citation_path(_usc_cite()) == Path("statute/USC/42/1983.md")


def test_path_ndcc():
    assert _citation_path(_ndcc_cite()) == Path("statute/NDCC/title-12.1/chapter-12.1-32.md")


def test_path_nd_const():
    assert _citation_path(_nd_const()) == Path("cnst/ND/art-01/sec-20.md")


def test_path_ndac():
    assert _citation_path(_ndac_cite()) == Path("reg/NDAC/title-43/article-43-02/chapter-43-02-05.md")


def test_path_cfr():
    cite = Citation(
        raw_text="29 C.F.R. § 1630.2",
        cite_type=CitationType.REGULATION, jurisdiction="us",
        normalized="29 C.F.R. § 1630.2",
        components={"title": "29", "section": "1630.2"},
    )
    assert _citation_path(cite) == Path("reg/CFR/29/1630.2.md")


def test_path_nd_court_rule():
    assert _citation_path(_nd_court_rule()) == Path("rule/ndrcivp/rule-56.md")


def test_path_federal_rule_frcp():
    assert _citation_path(_federal_rule()) == Path("rule/FRCP/rule-12.md")


def test_path_federal_rule_fre():
    cite = Citation(
        raw_text="Fed. R. Evid. 403",
        cite_type=CitationType.COURT_RULE, jurisdiction="us",
        normalized="Fed. R. Evid. 403",
        components={"rule_set": "fre", "rule_number": "403", "subsection": None},
    )
    assert _citation_path(cite) == Path("rule/FRE/rule-403.md")


def test_path_us_const_amendment():
    assert _citation_path(_us_const_amend()) == Path("cnst/US/amend-14.md")


def test_path_us_const_article_section():
    assert _citation_path(_us_const_article()) == Path("cnst/US/art-03/sec-2.md")


def test_path_us_const_article_only():
    cite = Citation(
        raw_text="U.S. Const. art. III",
        cite_type=CitationType.CONSTITUTION, jurisdiction="us",
        normalized="U.S. Const. art. III",
        components={"article": "III"},
    )
    assert _citation_path(cite) == Path("cnst/US/art-03.md")


def test_path_public_api():
    """citation_path() is the public wrapper around _citation_path()."""
    assert citation_path(_nd_opinion()) == _citation_path(_nd_opinion())


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
    path = tmp_path / "opin/ND/2024/2024ND156.md"
    path.parent.mkdir(parents=True)
    path.write_text("# 2024 ND 156\nOpinion text here.")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_federal_case(tmp_path):
    cite = _federal_case()
    path = tmp_path / "opin/US/505/377.md"
    path.parent.mkdir(parents=True)
    path.write_text("opinion")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_usc(tmp_path):
    cite = _usc_cite()
    path = tmp_path / "statute/USC/42/1983.md"
    path.parent.mkdir(parents=True)
    path.write_text("statute")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_ndcc(tmp_path):
    cite = _ndcc_cite()
    path = tmp_path / "statute/NDCC/title-12.1/chapter-12.1-32.md"
    path.parent.mkdir(parents=True)
    path.write_text("chapter")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_nd_const(tmp_path):
    cite = _nd_const()
    path = tmp_path / "cnst/ND/art-01/sec-20.md"
    path.parent.mkdir(parents=True)
    path.write_text("section")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_court_rule(tmp_path):
    cite = _nd_court_rule()
    path = tmp_path / "rule/ndrcivp/rule-56.md"
    path.parent.mkdir(parents=True)
    path.write_text("rule")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_ndac(tmp_path):
    cite = _ndac_cite()
    path = tmp_path / "reg/NDAC/title-43/article-43-02/chapter-43-02-05.md"
    path.parent.mkdir(parents=True)
    path.write_text("admin rule")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_nw2d_reporter(tmp_path):
    """All reporters resolve under opin/{reporter}/."""
    cite = Citation(
        raw_text="355 N.W.2d 16",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="355 N.W.2d 16",
        components={"volume": "355", "reporter": "N.W.2d", "page": "16"},
    )
    path = tmp_path / "opin/NW2d/355/16.md"
    path.parent.mkdir(parents=True)
    path.write_text("opinion")
    assert resolve_local(cite, tmp_path) == path


def test_resolve_local_state_reporter(tmp_path):
    """All reporters resolve under opin/{reporter}/."""
    cite = Citation(
        raw_text="800 P.2d 500",
        cite_type=CitationType.CASE, jurisdiction="us",
        normalized="800 P.2d 500",
        components={"volume": "800", "reporter": "P.2d", "page": "500"},
    )
    path = tmp_path / "opin/P2d/800/500.md"
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


def test_cache_content_readonly_returns_none(tmp_path):
    """cache_content returns None without error on a read-only refs dir."""
    cite = _nd_opinion()
    readonly_dir = tmp_path / "readonly_refs"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o555)
    result = cache_content(cite, "content", readonly_dir)
    assert result is None
    # Restore permissions for cleanup
    readonly_dir.chmod(0o755)


def test_cache_content_nonexistent_parent_readonly(tmp_path):
    """cache_content returns None when parent can't be created."""
    cite = _nd_opinion()
    # Point at a path inside a non-existent dir on a read-only mount
    result = cache_content(cite, "content", Path("/nonexistent/refs"))
    assert result is None


def test_cache_roundtrip(tmp_path):
    """Cache content, then resolve it."""
    cite = _nd_opinion()
    cache_content(cite, "cached opinion", tmp_path)
    found = resolve_local(cite, tmp_path)
    assert found is not None
    assert found.read_text() == "cached opinion"


def test_cache_content_original_html(tmp_path):
    """cache_content stores original HTML as dot-prefixed sibling."""
    cite = _nd_opinion()
    original = b"<html><body>Opinion</body></html>"
    path = cache_content(cite, "# Opinion", tmp_path,
                         original=original, original_content_type="text/html")
    assert path is not None
    orig_path = path.parent / f".{path.stem}.orig.html"
    assert orig_path.is_file()
    assert orig_path.read_bytes() == original


def test_cache_content_original_pdf(tmp_path):
    """cache_content stores original PDF as dot-prefixed sibling."""
    cite = _federal_case()
    original = b"%PDF-1.4 fake pdf content"
    path = cache_content(cite, "# Opinion", tmp_path,
                         original=original, original_content_type="application/pdf")
    orig_path = path.parent / f".{path.stem}.orig.pdf"
    assert orig_path.is_file()
    assert orig_path.read_bytes() == original


def test_cache_content_content_hash(tmp_path):
    """cache_content records SHA-256 of original in metadata."""
    cite = _nd_opinion()
    original = b"test content for hashing"
    path = cache_content(cite, "# Opinion", tmp_path,
                         original=original, original_content_type="text/html")
    meta = read_meta(path)
    assert "content_hash" in meta
    import hashlib
    expected = f"sha256:{hashlib.sha256(original).hexdigest()}"
    assert meta["content_hash"] == expected


def test_cache_content_http_headers(tmp_path):
    """cache_content records ETag and Last-Modified from HTTP headers."""
    cite = _nd_opinion()
    headers = {"ETag": '"abc123"', "Last-Modified": "Thu, 01 Jan 2026 00:00:00 GMT"}
    path = cache_content(cite, "# Opinion", tmp_path, http_headers=headers)
    meta = read_meta(path)
    assert meta["etag"] == '"abc123"'
    assert meta["last_modified"] == "Thu, 01 Jan 2026 00:00:00 GMT"


def test_cache_content_http_headers_lowercase(tmp_path):
    """cache_content handles lowercase HTTP header keys."""
    cite = _nd_opinion()
    headers = {"etag": '"def456"', "last-modified": "Fri, 02 Jan 2026 00:00:00 GMT"}
    path = cache_content(cite, "# Opinion", tmp_path, http_headers=headers)
    meta = read_meta(path)
    assert meta["etag"] == '"def456"'
    assert meta["last_modified"] == "Fri, 02 Jan 2026 00:00:00 GMT"


def test_cache_content_original_metadata_fields(tmp_path):
    """cache_content records original_content_type and original_file in meta."""
    cite = _nd_opinion()
    original = b"<html>test</html>"
    path = cache_content(cite, "# Opinion", tmp_path,
                         original=original, original_content_type="text/html")
    meta = read_meta(path)
    assert meta["original_content_type"] == "text/html"
    assert meta["original_file"] == f".{path.stem}.orig.html"


def test_cache_content_legacy_raw_html(tmp_path):
    """raw_html parameter still works for backward compatibility."""
    cite = _nd_opinion()
    path = cache_content(cite, "# Opinion", tmp_path,
                         raw_html="<html>legacy</html>")
    orig_path = path.parent / f".{path.stem}.orig.html"
    assert orig_path.is_file()
    assert orig_path.read_bytes() == b"<html>legacy</html>"
    meta = read_meta(path)
    assert "content_hash" in meta


def test_cache_content_no_original(tmp_path):
    """cache_content without original omits original fields from meta."""
    cite = _nd_opinion()
    path = cache_content(cite, "# Opinion", tmp_path)
    meta = read_meta(path)
    assert "original_content_type" not in meta
    assert "original_file" not in meta
    assert "content_hash" not in meta


# ── write_meta ─────────────────────────────────────────────────


def test_write_meta_creates_sidecar(tmp_path):
    path = tmp_path / "test.md"
    path.write_text("content")
    write_meta(path, {"citation": "test", "fetched": "now"})
    meta_path = path.with_suffix(".md.meta.json")
    assert meta_path.is_file()
    meta = json.loads(meta_path.read_text())
    assert meta["citation"] == "test"


def test_write_meta_overwrites(tmp_path):
    path = tmp_path / "test.md"
    path.write_text("content")
    write_meta(path, {"fetched": "old"})
    write_meta(path, {"fetched": "new"})
    meta = json.loads(path.with_suffix(".md.meta.json").read_text())
    assert meta["fetched"] == "new"


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

    html = "<h1>2024 ND 156</h1><p>Fetched opinion.</p>"
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.content = html.encode("utf-8")
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

    # Original should be saved as dot-prefixed sibling
    orig_path = path.parent / f".{path.stem}.orig.html"
    assert orig_path.is_file()

    # Metadata should include content hash and original info
    meta = read_meta(path)
    assert "content_hash" in meta
    assert meta["original_content_type"] == "text/html"


def test_fetch_and_cache_skips_if_cached(tmp_path):
    """fetch_and_cache should not re-download if already cached."""
    cite = _nd_opinion()
    cache_content(cite, "already cached", tmp_path)

    with patch("jetcite.cache.httpx.get") as mock_get:
        path = fetch_and_cache(cite, refs_dir=tmp_path)

    assert path is not None
    assert path.read_text() == "already cached"
    mock_get.assert_not_called()


def test_fetch_and_cache_force_overwrites(tmp_path):
    """fetch_and_cache with force=True should re-fetch even when cached."""
    cite = _nd_opinion()
    cache_content(cite, "old content", tmp_path)

    html = "<p>New content.</p>"
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.content = html.encode("utf-8")
    mock_resp.headers = {"content-type": "text/html; charset=utf-8"}
    mock_resp.raise_for_status = MagicMock()

    with patch("jetcite.cache.httpx.get", return_value=mock_resp) as mock_get:
        path = fetch_and_cache(cite, refs_dir=tmp_path, force=True)

    assert path is not None
    assert "New content" in path.read_text()
    mock_get.assert_called_once()


def test_fetch_and_cache_sends_user_agent(tmp_path):
    """fetch_and_cache should send a User-Agent header."""
    cite = _nd_opinion()

    html = "<p>Opinion text.</p>"
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.content = html.encode("utf-8")
    mock_resp.headers = {"content-type": "text/html; charset=utf-8"}
    mock_resp.raise_for_status = MagicMock()

    with patch("jetcite.cache.httpx.get", return_value=mock_resp) as mock_get:
        fetch_and_cache(cite, refs_dir=tmp_path)

    call_kwargs = mock_get.call_args
    assert "User-Agent" in call_kwargs.kwargs.get("headers", {})
    assert "jetcite" in call_kwargs.kwargs["headers"]["User-Agent"]


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


# ── pdf_to_text ────────────────────────────────────────────────


def test_pdf_to_text():
    """pdf_to_text extracts text from valid PDF bytes."""
    from jetcite.cache import pdf_to_text
    # Create a minimal valid PDF with text
    import io
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf)
        c.drawString(72, 720, "Hello from PDF")
        c.save()
        text = pdf_to_text(buf.getvalue())
        assert "Hello from PDF" in text
    except ImportError:
        # reportlab not installed — test with pdfplumber's own test logic
        pytest.skip("reportlab not available for PDF generation")


def test_pdf_to_text_invalid():
    """pdf_to_text returns empty string for invalid bytes."""
    from jetcite.cache import pdf_to_text
    assert pdf_to_text(b"not a pdf") == ""


def test_fetch_generic_pdf(tmp_path):
    """_fetch_generic handles application/pdf Content-Type."""
    from jetcite.cache import _fetch_generic

    mock_resp = MagicMock()
    mock_resp.content = b"%PDF-fake"
    mock_resp.headers = {"content-type": "application/pdf"}
    mock_resp.raise_for_status = MagicMock()

    with patch("jetcite.cache.httpx.get", return_value=mock_resp), \
         patch("jetcite.cache.pdf_to_text", return_value="Extracted text") as mock_pdf:
        content, meta, orig, ct, headers = _fetch_generic(
            "https://example.com/doc.pdf", _nd_opinion())

    assert content == "Extracted text"
    assert ct == "application/pdf"
    assert orig == b"%PDF-fake"
    mock_pdf.assert_called_once_with(b"%PDF-fake")


# ── conditional re-fetch (Phase 5) ───────────────────────────────


def test_refresh_stale_not_stale(tmp_path):
    """refresh_stale=True with fresh content should not re-fetch."""
    cite = _nd_opinion()
    cache_content(cite, "fresh opinion", tmp_path)

    with patch("jetcite.cache.httpx.get") as mock_get:
        path = fetch_and_cache(cite, refs_dir=tmp_path, refresh_stale=True)

    assert path is not None
    assert path.read_text() == "fresh opinion"
    mock_get.assert_not_called()


def test_refresh_stale_304_not_modified(tmp_path):
    """refresh_stale with 304 response just updates timestamp."""
    cite = _usc_cite()
    path = cache_content(cite, "statute text", tmp_path,
                         source_url="https://example.com/usc",
                         http_headers={"ETag": '"v1"'})
    # Make it stale
    meta = read_meta(path)
    meta["fetched"] = "2025-01-01T00:00:00+00:00"
    write_meta(path, meta)

    mock_resp_304 = MagicMock()
    mock_resp_304.status_code = 304

    with patch("jetcite.cache.httpx.get", return_value=mock_resp_304):
        result = fetch_and_cache(cite, refs_dir=tmp_path, refresh_stale=True)

    assert result is not None
    # Content unchanged
    assert result.read_text() == "statute text"
    # Timestamp updated
    new_meta = read_meta(result)
    assert new_meta["fetched"] != "2025-01-01T00:00:00+00:00"


def test_refresh_stale_same_hash(tmp_path):
    """refresh_stale with 200 but same content hash just updates metadata."""
    import hashlib

    cite = _usc_cite()
    original = b"<html>statute content</html>"
    path = cache_content(cite, "statute text", tmp_path,
                         source_url="https://example.com/usc",
                         original=original, original_content_type="text/html",
                         http_headers={"ETag": '"v1"'})
    # Make it stale
    meta = read_meta(path)
    meta["fetched"] = "2025-01-01T00:00:00+00:00"
    write_meta(path, meta)

    # Server returns 200 with same content
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = original  # same bytes
    mock_resp.headers = {"etag": '"v2"', "last-modified": "Fri, 01 Jan 2027 00:00:00 GMT"}
    mock_resp.raise_for_status = MagicMock()

    with patch("jetcite.cache.httpx.get", return_value=mock_resp):
        result = fetch_and_cache(cite, refs_dir=tmp_path, refresh_stale=True)

    assert result is not None
    assert result.read_text() == "statute text"  # content unchanged
    new_meta = read_meta(result)
    assert new_meta["etag"] == '"v2"'  # headers updated


# ── batch fetching (Phase 6) ──────────────────────────────────


def test_batch_sync_all_cached(tmp_path):
    """Batch fetch with all citations already cached makes no network calls."""
    from jetcite.cache import fetch_and_cache_batch_sync

    cite1 = _nd_opinion()
    cite2 = _usc_cite()
    cache_content(cite1, "opinion", tmp_path)
    cache_content(cite2, "statute", tmp_path)

    with patch("jetcite.cache.httpx.get") as mock_get:
        results = fetch_and_cache_batch_sync(
            [cite1, cite2], refs_dir=tmp_path, max_concurrent=2)

    assert len(results) == 2
    assert all(path is not None for _, path in results)
    mock_get.assert_not_called()


def test_batch_sync_mixed(tmp_path):
    """Batch fetch with mix of cached and uncached citations."""
    from jetcite.cache import fetch_and_cache_batch_sync

    cite_cached = _nd_opinion()
    cache_content(cite_cached, "already here", tmp_path)

    cite_new = _usc_cite()

    html = "<p>Fetched statute</p>"
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.content = html.encode("utf-8")
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.raise_for_status = MagicMock()

    with patch("jetcite.cache.httpx.get", return_value=mock_resp):
        results = fetch_and_cache_batch_sync(
            [cite_cached, cite_new], refs_dir=tmp_path, max_concurrent=2)

    assert len(results) == 2
    paths = {cite.normalized: path for cite, path in results}
    assert paths["2024 ND 156"] is not None
    assert paths["42 U.S.C. § 1983"] is not None


def test_batch_sync_callback(tmp_path):
    """Batch fetch calls on_complete for each citation."""
    from jetcite.cache import fetch_and_cache_batch_sync

    cite = _nd_opinion()
    cache_content(cite, "cached", tmp_path)

    completed = []
    def on_complete(c, p):
        completed.append((c.normalized, p is not None))

    fetch_and_cache_batch_sync(
        [cite], refs_dir=tmp_path, on_complete=on_complete)

    assert len(completed) == 1
    assert completed[0] == ("2024 ND 156", True)


# ── lookup/scan_text with refs_dir ─────────────────────────────


def test_lookup_with_refs_dir(tmp_path):
    """lookup() with refs_dir adds local source when cached."""
    # Pre-cache a known citation
    cached_path = tmp_path / "opin/ND/2024/2024ND156.md"
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
    cached_path = tmp_path / "opin/ND/2024/2024ND156.md"
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
