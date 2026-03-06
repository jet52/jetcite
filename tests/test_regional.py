"""Tests for regional and state reporter citation patterns."""

from jetcite.patterns.regional import RegionalReporterMatcher


def test_nw2d():
    m = RegionalReporterMatcher()
    results = m.find_all("585 N.W.2d 123")
    assert len(results) == 1
    assert results[0].normalized == "585 N.W. 2d 123"
    # ndcourts.gov is primary source for NW2d
    assert "ndcourts.gov" in results[0].sources[0].url
    # courtlistener is secondary
    assert any("courtlistener.com" in s.url for s in results[0].sources)


def test_a3d():
    m = RegionalReporterMatcher()
    results = m.find_all("200 A.3d 400")
    assert len(results) == 1
    assert results[0].normalized == "200 A. 3d 400"


def test_so_2d():
    m = RegionalReporterMatcher()
    results = m.find_all("300 So. 2d 100")
    assert len(results) == 1
    assert "So." in results[0].normalized


def test_p3d():
    m = RegionalReporterMatcher()
    results = m.find_all("150 P.3d 200")
    assert len(results) == 1


def test_cal_4th():
    m = RegionalReporterMatcher()
    results = m.find_all("50 Cal. 4th 300")
    assert len(results) == 1
    assert "Cal." in results[0].normalized


def test_ny_3d():
    m = RegionalReporterMatcher()
    results = m.find_all("35 N.Y.3d 100")
    assert len(results) == 1


def test_ohio_st_3d():
    m = RegionalReporterMatcher()
    results = m.find_all("160 Ohio St. 3d 200")
    assert len(results) == 1


def test_malformed_nw2d():
    m = RegionalReporterMatcher()
    results = m.find_all("585 NW2d 123")
    assert len(results) == 1


def test_nd_reports():
    """North Dakota Reports (state reporter, volumes 1-79, 1890-1953)."""
    m = RegionalReporterMatcher()
    results = m.find_all("50 N.D. 123")
    assert len(results) == 1
    assert results[0].normalized == "50 N.D. 123"
    assert results[0].jurisdiction == "nd"
    # N.D. Reports not searchable on ndcourts.gov; CourtListener only
    assert "courtlistener.com" in results[0].sources[0].url
    assert all("ndcourts.gov" not in s.url for s in results[0].sources)


def test_nd_reports_not_ndcc():
    """N.D. reporter should not match N.D.C.C."""
    m = RegionalReporterMatcher()
    results = m.find_all("N.D.C.C. § 1-02-13")
    nd_report_cites = [r for r in results if r.components.get("reporter") == "N.D."]
    assert len(nd_report_cites) == 0


def test_nw3d_ndcourts_search():
    """N.W.3d should get ndcourts.gov search URL."""
    m = RegionalReporterMatcher()
    results = m.find_all("993 N.W.3d 374")
    assert len(results) == 1
    assert any("ndcourts.gov" in s.url for s in results[0].sources)
    ndcourts_src = [s for s in results[0].sources if s.name == "ndcourts"][0]
    assert "cit1=993" in ndcourts_src.url
    assert "citType=NW3d" in ndcourts_src.url
    assert "cit2=374" in ndcourts_src.url


def test_nw_first_series_ndcourts():
    """N.W. first series should get ndcourts.gov search URL."""
    m = RegionalReporterMatcher()
    results = m.find_all("100 N.W. 500")
    assert len(results) == 1
    assert any("ndcourts.gov" in s.url for s in results[0].sources)


def test_a3d_no_ndcourts():
    """Atlantic reporter should NOT get ndcourts.gov URL."""
    m = RegionalReporterMatcher()
    results = m.find_all("200 A.3d 400")
    assert len(results) == 1
    assert all("ndcourts.gov" not in s.url for s in results[0].sources)
