"""ndlaw.org links and Citation.link_url (jetcite.links).

The contract under test: an ``ndlaw`` source is appended for North Dakota
authority ndlaw.org serves; ``link_url`` follows the caller's preference; and
``sources[0]`` -- the fetchable URL consumers fetch and ndlaw-mcp records in
its citation graph -- never changes, whatever the preference.
"""

import pytest

from jetcite import lookup, scan_text
from jetcite._egress import NON_FETCH_HOSTS
from jetcite.legacy import to_legacy_dict
from jetcite.links import resolve_preference
from jetcite.sources.ndlaw import ndlaw_cite_url

TEXT = (
    "State v. Schweitzer, 510 N.W.2d 612, 616 (N.D. 1994). Id. at 615. "
    "Peterson v. State, 2019 ND 140, ¶ 17, 927 N.W.2d 74. Id. ¶ 18. "
    "Rule 11(b)(1), N.D.R.Crim.P. Later, N.D.R.Crim.P. 11(c). "
    "N.D.C.C. § 12.1-32-09.1(1). N.D.A.C. § 75-02-01.2-01. "
    "N.D. Const. art. I, § 12. 2019 N.D. Sess. Laws ch. 404. "
    "Smith v. Jones, 600 N.W.2d 100, 105 (N.D. Ct. App. 1999). "
    "Doe v. Roe, 700 N.W.2d 1 (Minn. 2005). "
    "Haslam v. Babcock, 71 N.D. 363, 365, 1 N.W.2d 335 (1941). "
    "Local Rule 3. Fed. R. Civ. P. 56. 18 U.S.C. § 2."
)
BASE = "https://ndlaw.org/cite/"


def _scan(prefer=None):
    return scan_text(TEXT, resolve=False, include_pin_cites=True,
                     include_occurrences=True, prefer=prefer)


def _by(cites, normalized, nth=0):
    return [c for c in cites if c.normalized == normalized][nth]


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    monkeypatch.delenv("JETCITE_PREFER", raising=False)


def test_sources0_never_changes_with_preference(monkeypatch):
    official = [[s.url for s in c.sources][:1] for c in _scan("official")]
    assert official == [[s.url for s in c.sources][:1] for c in _scan("ndlaw")]
    monkeypatch.setenv("JETCITE_PREFER", "ndlaw")
    assert official == [[s.url for s in c.sources][:1] for c in _scan()]


def test_ndlaw_source_is_never_first():
    for c in _scan("ndlaw"):
        if c.sources:
            assert c.sources[0].name != "ndlaw", c.normalized


def test_official_preference_links_the_primary_url():
    for c in _scan("official"):
        assert c.link_url == (c.sources[0].url if c.sources else None)


@pytest.mark.parametrize("normalized, nth, link", [
    ("510 N.W.2d 612", 0, "State v. Schweitzer, 510 N.W.2d 612, 616"),
    ("2019 ND 140", 0, "2019 ND 140, ¶ 17"),
    ("927 N.W.2d 74", 0, "Peterson v. State, 927 N.W.2d 74"),
    ("N.D.R.Crim.P. 11", 0, "N.D.R.Crim.P. 11(b)(1)"),
    ("N.D.R.Crim.P. 11", 1, "N.D.R.Crim.P. 11(c)"),          # its own pinpoint
    ("N.D.C.C. § 12.1-32-09.1", 0, "N.D.C.C. § 12.1-32-09.1(1)"),
    ("N.D.A.C. § 75-02-01.2-01", 0, "N.D.A.C. § 75-02-01.2-01"),
    # a court parenthetical makes a bare N.W.2d cite North Dakota authority
    ("600 N.W.2d 100", 0, "Smith v. Jones, 600 N.W.2d 100, 105"),
    ("71 N.D. 363", 0, "Haslam v. Babcock, 71 N.D. 363, 365"),
    # ... and so does a parallel N.D. Reports cite
    ("1 N.W.2d 335", 0, "Haslam v. Babcock, 1 N.W.2d 335"),
])
def test_ndlaw_preference_links_ndlaw(normalized, nth, link):
    c = _by(_scan("ndlaw"), normalized, nth)
    assert c.link_url == ndlaw_cite_url(link)


def test_pin_cites_link_with_their_own_pinpoint():
    cites = _scan("ndlaw")
    pins = {c.raw_text: c for c in cites if c.is_pin_cite}
    assert pins["Id. at 615"].link_url == ndlaw_cite_url(
        "State v. Schweitzer, 510 N.W.2d 612, 615")
    assert pins["Id. ¶ 18"].link_url == ndlaw_cite_url("2019 ND 140, ¶ 18")


def test_source_is_authority_level_and_shared_by_repeats():
    cites = _scan("ndlaw")
    first, repeat = (_by(cites, "N.D.R.Crim.P. 11", i) for i in (0, 1))
    assert [s.url for s in repeat.sources] == [s.url for s in first.sources]
    nd = [s.url for s in first.sources if s.name == "ndlaw"]
    assert nd == [BASE + "N.D.R.Crim.P.%2011"]                 # no pinpoint


@pytest.mark.parametrize("normalized", [
    "700 N.W.2d 1",          # Minnesota: ndlaw.org would 404
    "Local Rule 3",          # district local rules: not in ndlaw
    "Fed. R. Civ. P. 56",
    "18 U.S.C. § 2",
])
def test_no_ndlaw_link_outside_its_corpus(normalized):
    c = _by(_scan("ndlaw"), normalized)
    assert all(s.name != "ndlaw" for s in c.sources)
    assert c.link_url == c.sources[0].url


@pytest.mark.parametrize("normalized", [
    "N.D. Const. art. I, § 12", "2019 N.D. Sess. Laws ch. 404"])
def test_constitution_and_session_laws_keep_their_links(normalized):
    # they carry an ndlaw source, but the preference does not move them
    c = _by(_scan("ndlaw"), normalized)
    assert any(s.name == "ndlaw" for s in c.sources)
    assert c.link_url == c.sources[0].url


def test_env_var_sets_the_preference(monkeypatch):
    monkeypatch.setenv("JETCITE_PREFER", "ndlaw")
    assert _by(_scan(), "2019 ND 140").link_url.startswith(BASE)
    # an explicit argument wins over the environment
    assert not _by(_scan("official"), "2019 ND 140").link_url.startswith(BASE)


def test_bad_preference_raises(monkeypatch):
    with pytest.raises(ValueError):
        scan_text("2019 ND 140", prefer="westlaw")
    monkeypatch.setenv("JETCITE_PREFER", "westlaw")
    with pytest.raises(ValueError):
        resolve_preference(None)


def test_lookup_honors_preference():
    c = lookup("State v. Schweitzer, 510 N.W.2d 612, 616 (N.D. 1994)",
               resolve=False, prefer="ndlaw")
    # lookup's input is the citation as written: ndlaw.org gets all of it
    assert c.link_url == ndlaw_cite_url(
        "State v. Schweitzer, 510 N.W.2d 612, 616 (N.D. 1994)")
    assert c.sources[0].name != "ndlaw"
    # no ND evidence, no ndlaw link
    c = lookup("510 N.W.2d 612", resolve=False, prefer="ndlaw")
    assert c.link_url == c.sources[0].url


def test_legacy_dict_carries_link_and_ndlaw_urls():
    d = to_legacy_dict(_by(_scan("ndlaw"), "2019 ND 140"))
    assert d["link_url"] == ndlaw_cite_url("2019 ND 140, ¶ 17")
    assert d["ndlaw_url"] == BASE + "2019%20ND%20140"
    assert not d["url"].startswith(BASE)
    d = to_legacy_dict(_by(_scan("official"), "2019 ND 140"))
    assert d["link_url"] == d["url"]


def test_ndlaw_is_link_only():
    assert "ndlaw.org" in NON_FETCH_HOSTS


def test_ndlaw_cite_url_encoding():
    assert ndlaw_cite_url("2019  ND 140, ¶ 17") == \
        BASE + "2019%20ND%20140,%20%C2%B6%2017"


def test_text_link_url_carries_only_a_pinpoint_in_the_text():
    cites = _scan("ndlaw")
    # a neutral cite's text carries its ¶ ('2019 ND 140, ¶ 17'), so the link may
    c = _by(cites, "2019 ND 140")
    assert "¶ 17" in c.raw_text
    assert c.text_link_url == ndlaw_cite_url("2019 ND 140, ¶ 17")
    # a reporter cite's page pin follows its text: every '510 N.W.2d 612'
    # links alike
    c = _by(cites, "510 N.W.2d 612")
    assert "616" not in c.raw_text
    assert c.text_link_url == ndlaw_cite_url("State v. Schweitzer, 510 N.W.2d 612")
    assert c.link_url == ndlaw_cite_url("State v. Schweitzer, 510 N.W.2d 612, 616")
    # the subdivision is part of the citation text
    assert _by(cites, "N.D.R.Crim.P. 11", 1).text_link_url == ndlaw_cite_url(
        "N.D.R.Crim.P. 11(c)")
    pins = {c.raw_text: c for c in cites if c.is_pin_cite}
    assert pins["Id. ¶ 18"].text_link_url == ndlaw_cite_url("2019 ND 140, ¶ 18")
    # under the official preference both are the primary URL
    c = _by(_scan("official"), "2019 ND 140")
    assert c.text_link_url == c.link_url == c.sources[0].url
