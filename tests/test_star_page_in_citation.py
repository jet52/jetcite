"""A star-page marker printed inside a citation must not stop the cite from matching."""
import pytest

from jetcite import scan_text


@pytest.mark.parametrize("text, norm, raw", [
    ("See Stonewood Hotel, 447 [*442] N.W.2d 286, 289 (N.D.1989).", "447 N.W.2d 286", "447 [*442] N.W.2d 286"),
    ("Granger v. Roll, 62 [*79] N.W. 970.", "62 N.W. 970", "62 [*79] N.W. 970"),
    ("Granger v. Roll, 62 N.W. [*79] 970.", "62 N.W. 970", "62 N.W. [*79] 970"),
    ("Buckley, 424 U.S. 507, 96 S.Ct. 1029, 47 [*431] L.Ed.2d 196 (1976).", "47 L. Ed. 2d 196", None),
    ("State v. Doe, 2012 [*5] ND 15, ¶ 6.", "2012 ND 15", "2012 [*5] ND 15"),
    ("State v. Roe, 71 N.D. 363, 1 [**335] N.W.2d 335.", "1 N.W.2d 335", "1 [**335] N.W.2d 335"),
])
def test_marker_inside_cite(text, norm, raw):
    cs = {c.normalized: c for c in scan_text(text, resolve=False)}
    assert norm in cs, sorted(cs)
    c = cs[norm]
    if raw:
        assert c.raw_text.startswith(raw)                  # a neutral cite's raw text runs on through its pinpoint
    assert text[c.position:c.position + len(c.raw_text)] == c.raw_text      # positions index the printed text


def test_unmarked_text_is_untouched():
    text = "See 447 N.W.2d 286, 289 (N.D.1989); N.D.C.C. § 28-04-07."
    cs = scan_text(text, resolve=False)
    assert [c.raw_text for c in cs if c.normalized == "447 N.W.2d 286"] == ["447 N.W.2d 286"]


def test_marker_between_cites_makes_no_cite():
    assert not [c for c in scan_text("the year 1950 [*12] and 300 people", resolve=False)]


def test_raw_text_is_restored_when_position_is_not_its_first_character():
    """A neutral cite's `position` can sit a few characters before the text it keeps;
    raw_text then held the mask's spaces (`2007 ND        20, ¶ 21`) instead of the marker."""
    from jetcite.models import Citation, CitationType
    from jetcite.scanner import _mask_star_pages, _restore_printed
    printed = "prevailing. *Hanson v. Boeder*, 2007 ND [*451] 20, ¶ 21, 727 N.W.2d 280."
    masked = _mask_star_pages(printed)
    start = masked.index("2007 ND")
    raw = masked[start:start + len("2007 ND [*451] 20, ¶ 21")]
    assert "    " in raw
    for off in (0, -8, 5):
        c = Citation(raw_text=raw, cite_type=CitationType.CASE, jurisdiction="nd",
                     normalized="2007 ND 20", position=start + off)
        _restore_printed([c], printed)
        assert c.raw_text == "2007 ND [*451] 20, ¶ 21", off


def test_padded_raw_text_without_a_marker_is_left_alone():
    from jetcite.models import Citation, CitationType
    from jetcite.scanner import _restore_printed
    printed = "160        S. E.        20        14"          # a table row, no marker
    c = Citation(raw_text="160        S. E.        20", cite_type=CitationType.CASE, jurisdiction="us",
                 normalized="160 S.E. 20", position=3)
    _restore_printed([c], printed)
    assert c.raw_text == "160        S. E.        20"
