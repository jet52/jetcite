"""Shared test configuration."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _no_network_resolve():
    """Disable ndcourts.gov URL resolution in all tests by default.

    Tests that need real resolution should use resolve=True explicitly
    or mock resolve_nd_opinion_url with a specific return value.
    """
    with patch("jetcite.scanner.resolve_nd_opinion_urls"):
        yield
