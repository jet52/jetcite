"""Tests for the link-only official-print U.S. Reports source."""

from jetcite.scanner import scan_text
from jetcite.sources.usreports import us_reports_official_pdf


def _sources(cite):
    return {s.name: s.url for s in cite.sources}


class TestOfficialPdfUrl:
    def test_loc_per_case_scan(self):
        assert us_reports_official_pdf("505", "377") == (
            "https://tile.loc.gov/storage-services/service/ll/usrep/"
            "usrep505/usrep505377/usrep505377.pdf"
        )

    def test_loc_zero_pads_volume_and_page(self):
        assert us_reports_official_pdf("5", "137") == (
            "https://tile.loc.gov/storage-services/service/ll/usrep/"
            "usrep005/usrep005137/usrep005137.pdf"
        )

    def test_bound_volume_above_loc_coverage(self):
        assert us_reports_official_pdf("580", "1") == (
            "https://www.supremecourt.gov/opinions/boundvolumes/580bv.pdf"
        )

    def test_no_url_above_bound_volume_coverage(self):
        assert us_reports_official_pdf("588", "1") is None

    def test_non_numeric_returns_none(self):
        assert us_reports_official_pdf("50x", "1") is None


class TestScanIntegration:
    def test_us_reports_cite_carries_official_pdf_source(self):
        cites = scan_text("R.A.V. v. St. Paul, 505 U.S. 377 (1992).",
                          resolve=False)
        us = [c for c in cites if c.normalized == "505 U.S. 377"]
        assert us, "U.S. Reports cite not found"
        srcs = _sources(us[0])
        assert srcs.get("official_pdf", "").endswith("usrep505377.pdf")
        # Fetchable sources still lead: extractor loop and generic fallback
        # must never reach the link-only source.
        assert us[0].sources[0].name == "justia"

    def test_legacy_dict_carries_official_pdf_url(self, tmp_path):
        from jetcite.legacy import to_legacy_dict
        cites = scan_text("Brown v. Board of Education, 347 U.S. 483 (1954).",
                          resolve=False)
        us = [c for c in cites if c.normalized == "347 U.S. 483"]
        assert us
        entry = to_legacy_dict(us[0], tmp_path)
        assert entry["official_pdf_url"].endswith("usrep347483.pdf")
        # The fetchable url is unchanged — still the Justia page.
        assert "supreme.justia.com" in entry["url"]

    def test_recent_volume_has_no_official_pdf_source(self):
        cites = scan_text("Some Case, 601 U.S. 416 (2024).", resolve=False)
        us = [c for c in cites if c.normalized == "601 U.S. 416"]
        assert us
        assert "official_pdf" not in _sources(us[0])
