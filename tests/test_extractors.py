"""Tests for source-specific content extractors and the fetch_and_cache router."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from jetcite.cache import fetch_and_cache, cache_content, _get_extractor
from jetcite.models import Citation, CitationType, Source
from jetcite.sources.courtlistener import (
    fetch_courtlistener,
    _clean_html_to_markdown,
    _fetch_via_citation_lookup,
    _fetch_via_search,
    _fetch_via_scrape,
    _fetch_opinion_text,
    _format_case_markdown,
)
from jetcite.sources.justia import fetch_justia, _extract_text


# ── Helpers ──────────────────────────────────────────────────────


def _nw2d_cite() -> Citation:
    """A NW2d case citation routed to CourtListener."""
    return Citation(
        raw_text="585 N.W.2d 123",
        cite_type=CitationType.CASE,
        jurisdiction="us",
        normalized="585 N.W.2d 123",
        components={"volume": "585", "reporter": "N.W.2d", "page": "123"},
        sources=[
            Source("courtlistener", "https://www.courtlistener.com/c/N.W.%202d/585/123/"),
        ],
    )


def _us_reports_cite() -> Citation:
    """A U.S. Reports citation routed to Justia."""
    return Citation(
        raw_text="392 U.S. 1",
        cite_type=CitationType.CASE,
        jurisdiction="us",
        normalized="392 U.S. 1",
        components={"volume": "392", "reporter": "U.S.", "page": "1"},
        sources=[
            Source("justia", "https://supreme.justia.com/cases/federal/us/392/1"),
            Source("courtlistener", "https://www.courtlistener.com/c/U.S./392/1/"),
        ],
    )


def _govinfo_cite() -> Citation:
    """A USC citation — no specific extractor, uses generic fallback."""
    return Citation(
        raw_text="42 U.S.C. § 1983",
        cite_type=CitationType.STATUTE,
        jurisdiction="us",
        normalized="42 U.S.C. § 1983",
        components={"title": "42", "section": "1983"},
        sources=[
            Source("govinfo", "https://www.govinfo.gov/link/uscode/42/1983?link-type=html"),
        ],
    )


# ── _get_extractor routing ────────────────────────────────────────


def test_router_courtlistener():
    extractor = _get_extractor("https://www.courtlistener.com/c/N.W.%202d/585/123/")
    assert extractor is fetch_courtlistener


def test_router_justia():
    extractor = _get_extractor("https://supreme.justia.com/cases/federal/us/392/1")
    assert extractor is fetch_justia


def test_router_unknown_host():
    extractor = _get_extractor("https://www.govinfo.gov/link/uscode/42/1983")
    assert extractor is None


def test_router_ndcourts_no_extractor():
    extractor = _get_extractor("https://www.ndcourts.gov/supreme-court/opinions/171302")
    assert extractor is None


# ── _clean_html_to_markdown ─────────────────────────────────────


def test_clean_html_paragraphs():
    html = "<p>First paragraph.</p><p>Second paragraph.</p>"
    md = _clean_html_to_markdown(html)
    assert "First paragraph." in md
    assert "Second paragraph." in md
    assert "<p>" not in md


def test_clean_html_headings():
    html = "<h2>Section One</h2><p>Content here.</p>"
    md = _clean_html_to_markdown(html)
    assert "## Section One" in md
    assert "Content here." in md


def test_clean_html_blockquote():
    html = "<blockquote>Quoted text here.</blockquote>"
    md = _clean_html_to_markdown(html)
    assert "> Quoted text here." in md


def test_clean_html_list():
    html = "<li>Item one</li><li>Item two</li>"
    md = _clean_html_to_markdown(html)
    assert "- Item one" in md
    assert "- Item two" in md


# ── _format_case_markdown ─────────────────────────────────────


def test_format_case_markdown():
    md = _format_case_markdown(
        case_name="State v. Baker",
        citation="2026 ND 42",
        court="North Dakota Supreme Court",
        date="2026-03-15",
        source="CourtListener API",
        body="The court held that the statute was valid.",
    )
    assert md.startswith("# State v. Baker")
    assert "**Citation:** 2026 ND 42" in md
    assert "**Court:** North Dakota Supreme Court" in md
    assert "**Date:** 2026-03-15" in md
    assert "---" in md
    assert "The court held that the statute was valid." in md


# ── Citation Lookup API (preferred) ──────────────────────────────


_CL_LOOKUP_RESPONSE = [
    {
        "citation": "585 N.W.2d 123",
        "normalized_citations": ["585 N.W.2d 123"],
        "status": 200,
        "clusters": [
            {
                "case_name": "State v. Smith",
                "date_filed": "1998-06-15",
                "court": "North Dakota Supreme Court",
                "sub_opinions": [
                    "https://www.courtlistener.com/api/rest/v4/opinions/12345/"
                ],
            }
        ],
    }
]

_CL_OPINION_RESPONSE = {
    "html_with_citations": (
        "<p>The defendant appeals from a criminal judgment.</p>"
        "<p>We affirm the conviction.</p>"
    ),
    "plain_text": "The defendant appeals...",
}


def test_citation_lookup_success():
    """Citation Lookup API → cluster → opinion text → markdown."""
    mock_lookup = MagicMock()
    mock_lookup.status_code = 200
    mock_lookup.json.return_value = _CL_LOOKUP_RESPONSE

    mock_opinion = MagicMock()
    mock_opinion.status_code = 200
    mock_opinion.json.return_value = _CL_OPINION_RESPONSE

    def mock_request(url_or_method, *args, **kwargs):
        # httpx.post for lookup, httpx.get for opinion
        if "opinions" in str(url_or_method) or "opinions" in str(kwargs.get("url", "")):
            return mock_opinion
        return mock_lookup

    with patch("jetcite.sources.courtlistener.httpx.post", return_value=mock_lookup), \
         patch("jetcite.sources.courtlistener.httpx.get", return_value=mock_opinion):
        content, meta = _fetch_via_citation_lookup(
            volume="585", reporter="N.W.2d", page="123",
            normalized="585 N.W.2d 123",
            token="test-token",
        )

    assert content is not None
    assert "# State v. Smith" in content
    assert "**Court:** North Dakota Supreme Court" in content
    assert "The defendant appeals from a criminal judgment." in content
    assert meta["case_name"] == "State v. Smith"
    assert meta["date_filed"] == "1998-06-15"


def test_citation_lookup_no_results():
    """Citation Lookup returns empty array → None."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []

    with patch("jetcite.sources.courtlistener.httpx.post", return_value=mock_resp):
        content, meta = _fetch_via_citation_lookup(
            volume="999", reporter="N.W.2d", page="999",
            normalized="999 N.W.2d 999",
            token="test-token",
        )

    assert content is None


def test_citation_lookup_404_status():
    """Citation Lookup returns status 404 for a valid but unknown cite."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"citation": "999 N.W.2d 999", "status": 404, "clusters": [],
         "error_message": "Citation not found"},
    ]

    with patch("jetcite.sources.courtlistener.httpx.post", return_value=mock_resp):
        content, meta = _fetch_via_citation_lookup(
            volume="999", reporter="N.W.2d", page="999",
            normalized="999 N.W.2d 999",
            token="test-token",
        )

    assert content is None


def test_citation_lookup_http_error():
    """HTTP error from the lookup endpoint → None."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("jetcite.sources.courtlistener.httpx.post", return_value=mock_resp):
        content, meta = _fetch_via_citation_lookup(
            volume="585", reporter="N.W.2d", page="123",
            normalized="585 N.W.2d 123",
            token="test-token",
        )

    assert content is None


def test_citation_lookup_opinion_plain_text_fallback():
    """When opinion has no HTML, fall back to plain_text."""
    mock_lookup = MagicMock()
    mock_lookup.status_code = 200
    mock_lookup.json.return_value = _CL_LOOKUP_RESPONSE

    mock_opinion = MagicMock()
    mock_opinion.status_code = 200
    mock_opinion.json.return_value = {
        "html_with_citations": "",
        "html": "",
        "plain_text": "Plain text opinion from CL.",
    }

    with patch("jetcite.sources.courtlistener.httpx.post", return_value=mock_lookup), \
         patch("jetcite.sources.courtlistener.httpx.get", return_value=mock_opinion):
        content, meta = _fetch_via_citation_lookup(
            volume="585", reporter="N.W.2d", page="123",
            normalized="585 N.W.2d 123",
            token="test-token",
        )

    assert content is not None
    assert "Plain text opinion from CL." in content


# ── _fetch_opinion_text ──────────────────────────────────────────


def test_fetch_opinion_text_html_with_citations():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "html_with_citations": "<p>Opinion paragraph.</p>",
    }

    with patch("jetcite.sources.courtlistener.httpx.get", return_value=mock_resp):
        text = _fetch_opinion_text(
            "https://www.courtlistener.com/api/rest/v4/opinions/123/",
            {"Authorization": "Token test"},
            timeout=10.0,
        )

    assert text is not None
    assert "Opinion paragraph." in text
    assert "<p>" not in text


def test_fetch_opinion_text_plain_text_fallback():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "plain_text": "Plain text only opinion.",
    }

    with patch("jetcite.sources.courtlistener.httpx.get", return_value=mock_resp):
        text = _fetch_opinion_text(
            "https://www.courtlistener.com/api/rest/v4/opinions/123/",
            {"Authorization": "Token test"},
            timeout=10.0,
        )

    assert text == "Plain text only opinion."


def test_fetch_opinion_text_empty():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {}

    with patch("jetcite.sources.courtlistener.httpx.get", return_value=mock_resp):
        text = _fetch_opinion_text(
            "https://www.courtlistener.com/api/rest/v4/opinions/123/",
            {"Authorization": "Token test"},
            timeout=10.0,
        )

    assert text is None


# ── fetch_courtlistener dispatch ─────────────────────────────────


def test_fetch_courtlistener_prefers_lookup_when_token_set():
    """With COURTLISTENER_TOKEN set, should try Citation Lookup first."""
    cite = _nw2d_cite()

    with patch("jetcite.sources.courtlistener._get_token", return_value="test-token"), \
         patch("jetcite.sources.courtlistener._fetch_via_citation_lookup",
               return_value=("# Mocked lookup result", {"case_name": "Test"})) as mock_lookup, \
         patch("jetcite.sources.courtlistener._fetch_via_search") as mock_search:
        content, meta = fetch_courtlistener(cite.sources[0].url, cite)

    mock_lookup.assert_called_once()
    mock_search.assert_not_called()
    assert "Mocked lookup result" in content


def test_fetch_courtlistener_falls_back_to_search_without_token():
    """Without token, should skip lookup and use search API."""
    cite = _nw2d_cite()

    with patch("jetcite.sources.courtlistener._get_token", return_value=None), \
         patch("jetcite.sources.courtlistener._fetch_via_citation_lookup") as mock_lookup, \
         patch("jetcite.sources.courtlistener._fetch_via_search",
               return_value=("# Search result", {"case_name": "Test"})) as mock_search:
        content, meta = fetch_courtlistener(cite.sources[0].url, cite)

    mock_lookup.assert_not_called()
    mock_search.assert_called_once()
    assert "Search result" in content


def test_fetch_courtlistener_lookup_fail_falls_to_search():
    """If lookup fails, should fall through to search API."""
    cite = _nw2d_cite()

    with patch("jetcite.sources.courtlistener._get_token", return_value="test-token"), \
         patch("jetcite.sources.courtlistener._fetch_via_citation_lookup",
               return_value=(None, {})) as mock_lookup, \
         patch("jetcite.sources.courtlistener._fetch_via_search",
               return_value=("# Search fallback", {"case_name": "Test"})) as mock_search:
        content, meta = fetch_courtlistener(cite.sources[0].url, cite)

    mock_lookup.assert_called_once()
    mock_search.assert_called_once()
    assert "Search fallback" in content


# ── Search API fallback ──────────────────────────────────────────


_CL_SEARCH_RESPONSE = {
    "results": [
        {
            "caseName": "State v. Smith",
            "dateFiled": "2020-06-15",
            "court": "North Dakota Supreme Court",
            "html_with_citations": (
                "<p>The defendant appeals from a criminal judgment.</p>"
                "<p>We affirm the conviction.</p>"
            ),
            "plain_text": "The defendant appeals...",
        }
    ]
}


def test_fetch_via_search_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _CL_SEARCH_RESPONSE

    with patch("jetcite.sources.courtlistener.httpx.get", return_value=mock_resp):
        content, meta = _fetch_via_search("585 N.W.2d 123")

    assert content is not None
    assert "# State v. Smith" in content
    assert "**Court:** North Dakota Supreme Court" in content
    assert "The defendant appeals from a criminal judgment." in content
    assert meta["case_name"] == "State v. Smith"


def test_fetch_via_search_no_results():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": []}

    with patch("jetcite.sources.courtlistener.httpx.get", return_value=mock_resp):
        content, meta = _fetch_via_search("999 N.W.2d 999")

    assert content is None


def test_fetch_via_search_http_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("jetcite.sources.courtlistener.httpx.get", return_value=mock_resp):
        content, meta = _fetch_via_search("585 N.W.2d 123")

    assert content is None


def test_fetch_via_search_plain_text_fallback():
    """When html_with_citations is empty, fall back to plain_text."""
    resp_data = {
        "results": [
            {
                "caseName": "State v. Jones",
                "dateFiled": "2021-01-10",
                "court": "Some Court",
                "html_with_citations": "",
                "plain_text": "Plain text opinion content here.",
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = resp_data

    with patch("jetcite.sources.courtlistener.httpx.get", return_value=mock_resp):
        content, meta = _fetch_via_search("100 N.W.2d 50")

    assert content is not None
    assert "Plain text opinion content here." in content


# ── CourtListener scrape fallback ────────────────────────────────


def test_fetch_via_scrape_success():
    html = """
    <html>
    <title>State v. Doe - CourtListener</title>
    <body>
    <article>
        <p>The defendant was convicted of theft.</p>
        <p>We reverse and remand.</p>
    </article>
    </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_resp.url = "https://www.courtlistener.com/opinion/12345/state-v-doe/"

    with patch("jetcite.sources.courtlistener.httpx.get", return_value=mock_resp):
        content, meta = _fetch_via_scrape(
            "https://www.courtlistener.com/c/N.W.%202d/500/100/",
            "500 N.W.2d 100",
        )

    assert content is not None
    assert "State v. Doe" in content
    assert "The defendant was convicted of theft." in content


def test_fetch_via_scrape_no_content():
    html = "<html><body><p>No opinion here</p></body></html>"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_resp.url = "https://www.courtlistener.com/opinion/12345/"

    with patch("jetcite.sources.courtlistener.httpx.get", return_value=mock_resp):
        content, meta = _fetch_via_scrape(
            "https://www.courtlistener.com/c/N.W.%202d/500/100/",
            "500 N.W.2d 100",
        )

    assert content is None


# ── Justia extractor ─────────────────────────────────────────────


def test_fetch_justia_success():
    html = """
    <html>
    <title>Terry v. Ohio - 392 U.S. 1 (1968) - Justia</title>
    <body>
    <h1>Terry v. Ohio</h1>
    <div id="tab-opinion">
        <p>This case presents serious questions concerning the role of the
        Fourth Amendment in the confrontation on the street.</p>
        <p>We affirm the conviction.</p>
    </div>
    </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html

    cite = _us_reports_cite()
    with patch("jetcite.sources.justia.httpx.get", return_value=mock_resp):
        content, meta = fetch_justia(cite.sources[0].url, cite)

    assert content is not None
    assert "# Terry v. Ohio" in content
    assert "**Citation:** 392 U.S. 1" in content
    assert "Supreme Court of the United States" in content
    assert "Fourth Amendment" in content
    assert meta["case_name"] == "Terry v. Ohio"


def test_fetch_justia_no_opinion_div():
    html = "<html><body><p>Page not found</p></body></html>"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html

    cite = _us_reports_cite()
    with patch("jetcite.sources.justia.httpx.get", return_value=mock_resp):
        content, meta = fetch_justia(cite.sources[0].url, cite)

    assert content is None


def test_fetch_justia_http_error():
    import httpx as httpx_mod
    cite = _us_reports_cite()

    with patch("jetcite.sources.justia.httpx.get",
               side_effect=httpx_mod.TimeoutException("timeout")):
        content, meta = fetch_justia(cite.sources[0].url, cite)

    assert content is None


# ── fetch_and_cache router integration ────────────────────────────


def test_fetch_routes_to_courtlistener(tmp_path):
    """CourtListener URL should use the CL extractor, not generic."""
    cite = _nw2d_cite()

    mock_content = _format_case_markdown(
        case_name="State v. Test",
        citation="585 N.W.2d 123",
        court="ND Supreme Court",
        date="1999-01-01",
        source="CourtListener API",
        body="Test opinion body.",
    )

    with patch(
        "jetcite.sources.courtlistener.fetch_courtlistener",
        return_value=(mock_content, {"case_name": "State v. Test"}),
    ) as mock_cl:
        path = fetch_and_cache(cite, refs_dir=tmp_path)

    mock_cl.assert_called_once()
    assert path is not None
    content = path.read_text()
    assert "# State v. Test" in content
    assert "Test opinion body." in content


def test_fetch_routes_to_justia(tmp_path):
    """Justia URL should use the Justia extractor."""
    cite = _us_reports_cite()

    mock_content = "# Terry v. Ohio\n\n**Citation:** 392 U.S. 1\n\n---\n\nOpinion text."

    with patch(
        "jetcite.sources.justia.fetch_justia",
        return_value=(mock_content, {"case_name": "Terry v. Ohio"}),
    ) as mock_justia:
        path = fetch_and_cache(cite, refs_dir=tmp_path)

    mock_justia.assert_called_once()
    assert path is not None
    assert "Terry v. Ohio" in path.read_text()


def test_fetch_falls_back_to_generic(tmp_path):
    """Unknown host should fall back to generic markdownify."""
    cite = _govinfo_cite()

    mock_resp = MagicMock()
    mock_resp.text = "<html><body><p>Section 1983 text</p></body></html>"
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.raise_for_status = MagicMock()

    with patch("jetcite.cache.httpx.get", return_value=mock_resp):
        path = fetch_and_cache(cite, refs_dir=tmp_path)

    assert path is not None
    content = path.read_text()
    assert "1983" in content
    assert "<html>" not in content


def test_fetch_tries_next_source_on_extractor_failure(tmp_path):
    """If the specific extractor returns None, fall back to generic."""
    cite = Citation(
        raw_text="585 N.W.2d 123",
        cite_type=CitationType.CASE,
        jurisdiction="us",
        normalized="585 N.W.2d 123",
        components={"volume": "585", "reporter": "N.W.2d", "page": "123"},
        sources=[
            Source("courtlistener", "https://www.courtlistener.com/c/N.W.%202d/585/123/"),
        ],
    )

    # CL extractor fails
    with patch(
        "jetcite.sources.courtlistener.fetch_courtlistener",
        return_value=(None, {}),
    ):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><p>Fallback content</p></body></html>"
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.raise_for_status = MagicMock()

        with patch("jetcite.cache.httpx.get", return_value=mock_resp):
            path = fetch_and_cache(cite, refs_dir=tmp_path)

    assert path is not None
    content = path.read_text()
    assert "Fallback" in content


# ── CLI cache subcommand ─────────────────────────────────────────


def test_cli_cache_dryrun(tmp_path):
    """jetcite cache --dry-run should list citations without fetching."""
    from click.testing import CliRunner
    from jetcite.cli import main

    runner = CliRunner()
    result = runner.invoke(main, [
        "cache", "585 N.W.2d 123",
        "--refs-dir", str(tmp_path),
        "--dry-run",
    ])
    assert result.exit_code == 0
    assert "fetch" in result.output
    assert "N.W." in result.output  # normalized form: 585 N.W. 2d 123


def test_cli_cache_status_missing(tmp_path):
    """jetcite cache --status should show 'missing' for uncached citations."""
    from click.testing import CliRunner
    from jetcite.cli import main

    runner = CliRunner()
    result = runner.invoke(main, [
        "cache", "585 N.W.2d 123",
        "--refs-dir", str(tmp_path),
        "--status",
    ])
    assert result.exit_code == 0
    assert "missing" in result.output


def test_cli_cache_status_cached(tmp_path):
    """jetcite cache --status should show 'cached' for cached citations."""
    from click.testing import CliRunner
    from jetcite.cli import main
    from jetcite.scanner import lookup

    # Pre-cache
    cite = lookup("585 N.W.2d 123")
    cache_content(cite, "cached content", tmp_path,
                  source_url="https://example.com")

    runner = CliRunner()
    result = runner.invoke(main, [
        "cache", "585 N.W.2d 123",
        "--refs-dir", str(tmp_path),
        "--status",
    ])
    assert result.exit_code == 0
    assert "cached" in result.output


def test_cli_cache_file_dryrun(tmp_path):
    """jetcite cache --file --dry-run should scan a document."""
    from click.testing import CliRunner
    from jetcite.cli import main

    fixture = Path(__file__).parent / "fixtures" / "sample_opinion.txt"
    runner = CliRunner()
    result = runner.invoke(main, [
        "cache", "--file", str(fixture),
        "--refs-dir", str(tmp_path),
        "--dry-run",
    ])
    assert result.exit_code == 0
    # Should list multiple citations
    assert "fetch" in result.output
    assert result.output.count("fetch") > 5
