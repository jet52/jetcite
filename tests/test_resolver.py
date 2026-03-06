"""Tests for the resolver module."""

from jetcite.models import Citation, CitationType, Source


def test_source_verified_default():
    s = Source(name="test", url="https://example.com")
    assert s.verified is None


def test_citation_defaults():
    c = Citation(
        raw_text="test",
        cite_type=CitationType.CASE,
        jurisdiction="us",
        normalized="test",
    )
    assert c.sources == []
    assert c.pinpoint is None
    assert c.components == {}
