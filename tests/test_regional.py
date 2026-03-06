"""Tests for regional and state reporter citation patterns."""

from jetcite.patterns.regional import RegionalReporterMatcher


def test_nw2d():
    m = RegionalReporterMatcher()
    results = m.find_all("585 N.W.2d 123")
    assert len(results) == 1
    assert results[0].normalized == "585 N.W. 2d 123"
    assert "courtlistener.com" in results[0].sources[0].url


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
