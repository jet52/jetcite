"""ndcourts.gov URL generation for ND opinions and court rules."""


def nd_opinion_url(year: str, number: str) -> str:
    """Generate an ndcourts.gov URL for an ND Supreme Court opinion."""
    return f"https://www.ndcourts.gov/supreme-court/opinion/{year}ND{number}"


def nd_court_rule_url(rule_set: str, parts: list[str]) -> str:
    """Generate an ndcourts.gov URL for a ND court rule."""
    joined = "-".join(parts)
    return f"https://www.ndcourts.gov/legal-resources/rules/{rule_set}/{joined}"


def nd_local_rule_url(rule: str) -> str:
    """Generate an ndcourts.gov search URL for a local rule."""
    return f"https://www.ndcourts.gov/legal-resources/rules/local/search?rule={rule}"


def nd_case_record_url(case_number: str) -> str:
    """Generate an ndcourts.gov URL for a case record."""
    return f"https://record.ndcourts.gov/{case_number}"


# Maps reporter names to the citType query parameter on ndcourts.gov
_NDCOURTS_CIT_TYPES = {
    "N.W.": "NW",
    "N.W.2d": "NW2d",
    "N.W. 2d": "NW2d",
    "N.W.3d": "NW3d",
    "N.W. 3d": "NW3d",
    "N.D.": "ND",
}


def nd_reporter_search_url(reporter: str, volume: str, page: str) -> str | None:
    """Generate an ndcourts.gov search URL for a NW/ND reporter citation.

    Returns None if the reporter is not a type searchable on ndcourts.gov.
    """
    cit_type = _NDCOURTS_CIT_TYPES.get(reporter)
    if not cit_type:
        return None
    return (
        f"https://www.ndcourts.gov/supreme-court/opinions"
        f"?cit1={volume}&citType={cit_type}&cit2={page}"
        f"&pageSize=10&sortOrder=1"
    )
