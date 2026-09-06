"""Tests for regional and state reporter citation patterns."""

from jetcite.patterns.regional import RegionalReporterMatcher


def test_nw2d():
    m = RegionalReporterMatcher()
    results = m.find_all("585 N.W.2d 123")
    assert len(results) == 1
    assert results[0].normalized == "585 N.W.2d 123"
    # CourtListener is the source for all NW citations
    assert "courtlistener.com" in results[0].sources[0].url


def test_a3d():
    m = RegionalReporterMatcher()
    results = m.find_all("200 A.3d 400")
    assert len(results) == 1
    assert results[0].normalized == "200 A.3d 400"


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


def test_nw3d_courtlistener_only():
    """N.W.3d should use CourtListener, not ndcourts.gov."""
    m = RegionalReporterMatcher()
    results = m.find_all("993 N.W.3d 374")
    assert len(results) == 1
    assert "courtlistener.com" in results[0].sources[0].url
    assert all("ndcourts.gov" not in s.url for s in results[0].sources)


def test_nw_first_series_courtlistener_only():
    """N.W. first series should use CourtListener, not ndcourts.gov."""
    m = RegionalReporterMatcher()
    results = m.find_all("100 N.W. 500")
    assert len(results) == 1
    assert "courtlistener.com" in results[0].sources[0].url
    assert all("ndcourts.gov" not in s.url for s in results[0].sources)


def test_a3d_no_ndcourts():
    """Atlantic reporter should NOT get ndcourts.gov URL."""
    m = RegionalReporterMatcher()
    results = m.find_all("200 A.3d 400")
    assert len(results) == 1
    assert all("ndcourts.gov" not in s.url for s in results[0].sources)


# ── Real citations from ND opinions ──────────────────────────────


def test_real_p2d():
    """673 P.2d 387 — Everett v. Trunnell (Idaho 1983), from 2024 ND 138."""
    m = RegionalReporterMatcher()
    results = m.find_all("673 P.2d 387")
    assert len(results) == 1
    assert results[0].components["volume"] == "673"
    assert results[0].components["page"] == "387"


def test_real_sw3d():
    """601 S.W.3d 168 — Carlisle v. Commonwealth (Ky. 2020), from 2024 ND 115."""
    m = RegionalReporterMatcher()
    results = m.find_all("601 S.W.3d 168")
    assert len(results) == 1


def test_real_ne3d():
    """204 N.E.3d 681 — State v. Byrd (Ohio), from 2024 ND 115."""
    m = RegionalReporterMatcher()
    results = m.find_all("204 N.E.3d 681")
    assert len(results) == 1


def test_real_so2d():
    """424 So.2d 1297 — Sheffield v. Exxon Corp. (Ala. 1982)."""
    m = RegionalReporterMatcher()
    results = m.find_all("424 So.2d 1297")
    assert len(results) == 1


def test_real_p3d():
    """478 P.3d 164 — Miller v. Life Care Centers (Wyo. 2020), from 2024 ND 149."""
    m = RegionalReporterMatcher()
    results = m.find_all("478 P.3d 164")
    assert len(results) == 1


# ── Truncation regression: pin-cite short forms (Gion redline 2026-04-25) ────


def test_so_3d_pin_cite_no_truncation():
    """`409 So. 3d at 188` must NOT produce a phantom `409 So. 3` citation."""
    m = RegionalReporterMatcher()
    results = m.find_all("Niemeyer, 409 So. 3d at 188.")
    assert results == []


def test_full_so_3d_then_pin_cite_dedup():
    """Full + pin cite combination yields exactly one entry."""
    m = RegionalReporterMatcher()
    text = (
        "Niemeyer v. Niemeyer, 409 So. 3d 186, 188 (Fla. Dist. Ct. App. 2025); "
        "see also id., 409 So. 3d at 190."
    )
    results = m.find_all(text)
    assert len(results) == 1
    assert results[0].normalized == "409 So. 3d 186"


def test_sw_3d_pin_cite_no_truncation():
    """Same regression check for S.W. reporter."""
    m = RegionalReporterMatcher()
    results = m.find_all("601 S.W.3d at 175")
    assert results == []


def test_se_2d_pin_cite_no_truncation():
    """Same regression check for S.E. reporter."""
    m = RegionalReporterMatcher()
    results = m.find_all("100 S.E.2d at 50")
    assert results == []


# ---- West bound-volume house style: spaced two-letter abbreviations --------
# West's older print style spaces the abbreviation ("49 N. D. 915, 194 N. W.
# 663"); ~4,350 westlaw-sourced ND opinions carry it. Normalized output stays
# compact so cross-links resolve.

def test_spaced_nd_reports():
    m = RegionalReporterMatcher()
    results = m.find_all("49 N. D. 915")
    assert [r.normalized for r in results] == ["49 N.D. 915"]


def test_spaced_nw_first_series():
    m = RegionalReporterMatcher()
    results = m.find_all("194 N. W. 663")
    assert [r.normalized for r in results] == ["194 N.W. 663"]


def test_spaced_nw2d():
    m = RegionalReporterMatcher()
    results = m.find_all("210 N. W. 2d 82")
    assert [r.normalized for r in results] == ["210 N.W.2d 82"]


def test_spaced_nd_not_ndcc():
    """Spaced 'N. D. C. C.' statute form must not yield a phantom N.D. case."""
    m = RegionalReporterMatcher()
    results = m.find_all("section 12.1-20-03, N. D. C. C., applies")
    assert results == []


def test_spaced_nw_linebreak():
    """The internal space may be a newline (print line wrap)."""
    m = RegionalReporterMatcher()
    results = m.find_all("194 N.\nW. 663")
    assert [r.normalized for r in results] == ["194 N.W. 663"]


# ── Phase 0 follow-up: N.D. Reports volume cap / no print N.D. App. ─────────


def test_four_digit_year_not_nd_reports():
    """`2024 N.D. 156` must not be eaten as Reports volume `024 N.D. 156`.

    N.D. Reports volumes are 1–79 (1890–1953). A 4-digit year + `N.D.` is a
    period-spelled neutral cite (`2024 ND 156`), never Reports.
    """
    from jetcite import lookup

    m = RegionalReporterMatcher()
    assert m.find_all("2024 N.D. 156") == []
    cite = lookup("2024 N.D. 156")
    assert cite is not None
    assert cite.normalized == "2024 ND 156"
    # Real Reports cites still parse.
    assert [r.normalized for r in m.find_all("1 N.D. 369")] == ["1 N.D. 369"]
    assert [r.normalized for r in m.find_all("50 N.D. 123")] == ["50 N.D. 123"]


def test_nd_reports_volume_cap():
    """Reports stopped at vol. 79; volumes >79 must not match as N.D. Reports."""
    m = RegionalReporterMatcher()
    assert m.find_all("224 N.D. 898") == []
    assert m.find_all("80 N.D. 1") == []
    assert [r.normalized for r in m.find_all("50 N.D. 123")] == ["50 N.D. 123"]
    assert [r.normalized for r in m.find_all("79 N.D. 1")] == ["79 N.D. 1"]
    assert [r.normalized for r in m.find_all("1 N.D. 369")] == ["1 N.D. 369"]


def test_no_nd_app_print_reporter():
    """There is no N.D. App. print reporter; `1 N.D. App. 1` must not parse."""
    from jetcite import lookup

    m = RegionalReporterMatcher()
    for text in ("1 N.D. App. 1", "1 N. D. App. 1"):
        assert m.find_all(text) == [], text
        assert lookup(text) is None, text


def test_nd_reports_does_not_match_ndcc_ndac():
    """N.D. Reports `(?!C|A)` guard must still protect N.D.C.C. / N.D.A.C."""
    m = RegionalReporterMatcher()
    for text in (
        "N.D.C.C. § 1-02-13",
        "N.D.A.C. § 43-02-05-01",
        "section 12.1-20-03, N. D. C. C., applies",
        "see N. D. A. C. § 75-02-04.1-01",
    ):
        nd_case = [r for r in m.find_all(text)
                   if r.components.get("reporter") == "N.D."]
        assert nd_case == [], text


def test_n_dak_reports():
    """Archaic `N. Dak.` / `N.Dak.` reporter spelling normalizes to N.D."""
    m = RegionalReporterMatcher()
    assert [r.normalized for r in m.find_all("1 N. Dak. 75")] == ["1 N.D. 75"]
    assert [r.normalized for r in m.find_all("2 N.Dak. 401")] == ["2 N.D. 401"]
    assert m.find_all("1 N. Dak. 75")[0].jurisdiction == "nd"


def test_n_dak_reports_year_tail_guard():
    """(?<!digit) year-tail guard on N. Dak. Reports: 4-digit years must not truncate."""
    m = RegionalReporterMatcher()
    assert m.find_all("2024 N. Dak. 156") == []
    assert m.find_all("1997 N.Dak. 24") == []
    # In-range archaic Reports still work.
    assert [r.normalized for r in m.find_all("79 N. Dak. 1")] == ["79 N.D. 1"]
    assert m.find_all("80 N. Dak. 1") == []
