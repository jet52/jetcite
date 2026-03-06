"""CourtListener URL generation for case citations."""

from urllib.parse import quote


def courtlistener_url(reporter: str, volume: str, page: str) -> str:
    """Generate a CourtListener URL for a case citation."""
    encoded = quote(reporter, safe="")
    return f"https://www.courtlistener.com/c/{encoded}/{volume}/{page}/"


def courtlistener_neutral_url(jurisdiction: str, year: str, number: str) -> str:
    """Generate a CourtListener URL for a neutral citation."""
    return f"https://www.courtlistener.com/c/{jurisdiction}/{year}/{number}/"
