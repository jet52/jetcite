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
