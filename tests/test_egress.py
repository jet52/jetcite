"""Guard tests keeping the network-egress allowlist and its docs in sync.

If a future revision adds a new legal-authority source domain, these tests
fail until the domain is added to ``EGRESS_ALLOWLIST`` *and* documented in
``jetcite/NETWORK.md`` (which ships with every vendored copy) and ``README.md``.
"""

import re
from pathlib import Path

from jetcite._egress import EGRESS_ALLOWLIST, NON_FETCH_HOSTS, covers

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src" / "jetcite"
_URL_HOST_RE = re.compile(r"https?://([A-Za-z0-9.-]+)")


def _hosts_referenced_in_source() -> set[str]:
    hosts: set[str] = set()
    for py in _SRC.rglob("*.py"):
        for match in _URL_HOST_RE.finditer(py.read_text(encoding="utf-8")):
            hosts.add(match.group(1).rstrip("."))
    return hosts


def test_every_source_host_is_allowlisted():
    """Any host jetcite hardcodes must be covered by EGRESS_ALLOWLIST."""
    referenced = _hosts_referenced_in_source() - set(NON_FETCH_HOSTS)
    missing = sorted(h for h in referenced if not covers(h))
    assert not missing, (
        "These hosts are referenced in jetcite source but not covered by "
        "EGRESS_ALLOWLIST in src/jetcite/_egress.py: "
        f"{missing}. Add each to EGRESS_ALLOWLIST, then document it in "
        "src/jetcite/NETWORK.md and README.md (or, if it is never fetched, "
        "add it to NON_FETCH_HOSTS)."
    )


def test_network_md_documents_every_entry():
    """NETWORK.md travels with vendored copies — it must list every entry."""
    network_md = (_SRC / "NETWORK.md").read_text(encoding="utf-8")
    missing = sorted(e for e in EGRESS_ALLOWLIST if e not in network_md)
    assert not missing, (
        f"src/jetcite/NETWORK.md is missing allowlist entries: {missing}"
    )


def test_readme_documents_every_entry():
    """The top-level README's allowlist section must list every entry."""
    readme = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
    missing = sorted(e for e in EGRESS_ALLOWLIST if e not in readme)
    assert not missing, f"README.md is missing allowlist entries: {missing}"
