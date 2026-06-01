"""Tests for egress-block detection and the user-facing warning."""

import urllib.error

import pytest

import jetcite._http as _http
from jetcite._http import (
    EgressBlockedWarning,
    HttpResponse,
    egress_blocked_hosts,
    http_get,
    reset_egress_blocked_hosts,
)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    reset_egress_blocked_hosts()
    # Force the urllib path so tests don't depend on httpx being installed.
    monkeypatch.setattr(_http, "httpx", None)
    yield
    reset_egress_blocked_hosts()


@pytest.mark.parametrize("message", [
    "Tunnel connection failed: 403 Forbidden",          # HTTP CONNECT proxy
    "Received HTTP code 403 from proxy after CONNECT",  # curl-style phrasing
    "Connection not allowed by ruleset (2)",            # SOCKS5 reply code 2
])
def test_proxy_denials_are_classified_as_egress_blocks(message):
    assert _http._is_egress_block(urllib.error.URLError(message))


@pytest.mark.parametrize("exc", [
    TimeoutError("timed out"),
    ConnectionRefusedError("Connection refused"),
    urllib.error.URLError("Name or service not known"),
])
def test_ordinary_failures_are_not_egress_blocks(exc):
    assert not _http._is_egress_block(exc)


def _raise(exc):
    def _fn(req, timeout=None):
        raise exc
    return _fn


def test_blocked_request_warns_and_records_host(monkeypatch):
    monkeypatch.setattr(
        _http.urllib.request, "urlopen",
        _raise(urllib.error.URLError("Tunnel connection failed: 403 Forbidden")),
    )
    with pytest.warns(EgressBlockedWarning, match="egress allowlist"):
        result = http_get("https://www.ndcourts.gov/supreme-court/opinions?x=1")
    assert result is None
    assert "www.ndcourts.gov" in egress_blocked_hosts()


def test_warning_is_deduplicated_per_host(monkeypatch, recwarn):
    monkeypatch.setattr(
        _http.urllib.request, "urlopen",
        _raise(urllib.error.URLError("Tunnel connection failed: 403 Forbidden")),
    )
    http_get("https://www.ndcourts.gov/a")
    http_get("https://www.ndcourts.gov/b")  # same host → no second warning
    assert sum(isinstance(w.message, EgressBlockedWarning) for w in recwarn) == 1


def test_ordinary_failure_does_not_warn_or_record(monkeypatch, recwarn):
    monkeypatch.setattr(
        _http.urllib.request, "urlopen", _raise(TimeoutError("timed out")),
    )
    assert http_get("https://www.ndcourts.gov/x") is None
    assert not egress_blocked_hosts()
    assert not [w for w in recwarn if isinstance(w.message, EgressBlockedWarning)]


def test_success_does_not_warn(monkeypatch, recwarn):
    class _Resp:
        status = 200
        headers = type("H", (), {"get_content_type": lambda self: "text/html"})()

        def read(self):
            return b"ok"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(_http.urllib.request, "urlopen", lambda req, timeout=None: _Resp())
    resp = http_get("https://www.ndcourts.gov/ok")
    assert isinstance(resp, HttpResponse) and resp.status_code == 200
    assert not egress_blocked_hosts()
    assert not [w for w in recwarn if isinstance(w.message, EgressBlockedWarning)]
