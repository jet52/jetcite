"""Justia URL generation and content extraction for U.S. Reports citations."""

from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup


def us_reports_url(volume: str, page: str) -> str:
    """Generate a Justia URL for a U.S. Reports citation."""
    return f"https://supreme.justia.com/cases/federal/us/{volume}/{page}"


def fetch_justia(
    source_url: str,
    citation: object,
    timeout: float = 10.0,
) -> tuple[str | None, dict]:
    """Fetch SCOTUS opinion content from Justia.

    Extracts opinion text from the case page.
    Returns (markdown_content, metadata_dict) or (None, {}) on failure.
    """
    try:
        resp = httpx.get(source_url, follow_redirects=True, timeout=timeout)
        if resp.status_code >= 400:
            return None, {}
    except (httpx.HTTPError, httpx.TimeoutException):
        return None, {}

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract case name from h1 or title
    h1 = soup.find("h1")
    case_name = h1.get_text(strip=True) if h1 else ""
    if not case_name:
        title_tag = soup.find("title")
        case_name = title_tag.get_text(strip=True) if title_tag else "Unknown"
        case_name = re.sub(r"\s*[-–|].*Justia.*$", "", case_name)

    # Extract opinion text — Justia puts it in #tab-opinion or similar containers
    opinion_div = (
        soup.find(id="tab-opinion")
        or soup.find(id="opinion")
        or soup.find(class_="tab-content")
    )

    if not opinion_div:
        # Try the main content area
        opinion_div = soup.find("div", class_="opinion-content")

    if not opinion_div:
        return None, {}

    body = _extract_text(opinion_div)
    if not body.strip():
        return None, {}

    # Try to extract metadata from the sidebar or header
    metadata = {"case_name": case_name}

    normalized = citation.normalized if hasattr(citation, "normalized") else ""

    lines = [f"# {case_name}", ""]
    if normalized:
        lines.append(f"**Citation:** {normalized}")
    lines.append(f"**Court:** Supreme Court of the United States")
    lines.append(f"**Source:** {source_url}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(body)

    return "\n".join(lines), metadata


def _extract_text(element) -> str:
    """Extract readable text from a BeautifulSoup element."""
    # Remove scripts and styles
    for tag in element.find_all(["script", "style", "nav"]):
        tag.decompose()

    paragraphs = []
    for el in element.find_all(["p", "h2", "h3", "h4", "blockquote"]):
        text = el.get_text(separator=" ", strip=True)
        if not text:
            continue
        if el.name.startswith("h"):
            level = int(el.name[1])
            paragraphs.append(f"{'#' * level} {text}")
        elif el.name == "blockquote":
            paragraphs.append(f"> {text}")
        else:
            paragraphs.append(text)

    if paragraphs:
        return "\n\n".join(paragraphs)

    # Fallback: just get all text with some structure
    return element.get_text(separator="\n\n", strip=True)
