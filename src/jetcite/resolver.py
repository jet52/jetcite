"""URL resolution and optional HTTP verification."""

from __future__ import annotations

import asyncio

import httpx

from jetcite.models import Citation, Source


async def _verify_url(client: httpx.AsyncClient, source: Source) -> None:
    """Verify a single URL with an HTTP HEAD request."""
    try:
        resp = await client.head(source.url, follow_redirects=True, timeout=10.0)
        source.verified = resp.status_code < 400
    except (httpx.HTTPError, httpx.TimeoutException):
        source.verified = False


async def verify_citations(
    citations: list[Citation],
    rate_limit: float = 1.0,
) -> None:
    """Verify all source URLs in a list of citations.

    Args:
        citations: Citations whose sources will be verified in-place.
        rate_limit: Minimum seconds between requests.
    """
    async with httpx.AsyncClient() as client:
        for cite in citations:
            for source in cite.sources:
                await _verify_url(client, source)
                if rate_limit > 0:
                    await asyncio.sleep(rate_limit)


def verify_citations_sync(
    citations: list[Citation],
    rate_limit: float = 1.0,
) -> None:
    """Synchronous wrapper for verify_citations."""
    asyncio.run(verify_citations(citations, rate_limit))
