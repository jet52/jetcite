# jetcite

American legal citation parser and linker. Parses legal citations from text, generates URLs to official government sources or reliable aggregators like courtlistener.com, and optionally verifies that URLs resolve.

## Install

```bash
pip install -e .
```

## CLI Usage

```bash
# Single citation → URL
jetcite "585 N.W.2d 123"
jetcite "N.D.C.C. § 12.1-32-01"
jetcite "2024 ND 156"

# Batch scan a document
jetcite --scan document.md
jetcite --scan - < brief.txt
cat opinion.txt | jetcite --scan -

# Output formats
jetcite --format json "2024 ND 156"
jetcite --scan document.md --format table
jetcite --scan document.md --format json

# Options
jetcite --verify "42 U.S.C. § 1983"    # HTTP-check the URL
jetcite --open "2024 ND 156"            # open in browser
jetcite --from-clipboard                 # read from clipboard (cross-platform)
jetcite --all-sources "2024 ND 156"     # show all URLs, not just primary
```

## Python API

The library exposes two main functions at the top level:

```python
from jetcite import lookup, scan_text
```

### `lookup(text) → Citation | None`

Parse a single citation string. Returns the first match, or `None`.

```python
from jetcite import lookup

cite = lookup("585 N.W.2d 123")
if cite:
    print(cite.normalized)        # "585 N.W. 2d 123"
    print(cite.cite_type.value)   # "case"
    print(cite.sources[0].url)    # "https://www.ndcourts.gov/..."
    print(cite.sources[0].name)   # "ndcourts"
```

### `scan_text(text) → list[Citation]`

Scan a document for all citations. Returns deduplicated results in document order with parallel citations detected and linked.

```python
from jetcite import scan_text

text = """The court held in 2024 ND 156, 10 N.W.3d 500, that
N.D.C.C. § 1-02-13 requires plain language interpretation."""

for cite in scan_text(text):
    print(cite.normalized, "→", cite.sources[0].url)
    if cite.parallel_cites:
        print(f"  (same case as {', '.join(cite.parallel_cites)})")
```

### `Citation.to_dict() → dict`

Convert a citation to a plain dictionary for JSON serialization:

```python
import json
from jetcite import scan_text

citations = scan_text(document_text)
print(json.dumps([c.to_dict() for c in citations], indent=2))
```

Output:

```json
[
  {
    "raw_text": "2024 ND 156",
    "cite_type": "case",
    "jurisdiction": "nd",
    "normalized": "2024 ND 156",
    "parallel_cites": ["10 N.W. 3d 500"],
    "sources": [
      {"name": "ndcourts", "url": "https://www.ndcourts.gov/supreme-court/opinion/2024ND156"},
      {"name": "courtlistener", "url": "https://www.courtlistener.com/c/ND/2024/156/"}
    ]
  }
]
```

## Using jetcite from a Claude Skill

### As an imported library

If jetcite is installed in the skill's Python environment, import and call directly:

```python
# In your skill's Python script
from jetcite import lookup, scan_text
import json

def find_citations(text: str) -> str:
    """Scan text for legal citations and return JSON results."""
    citations = scan_text(text)
    return json.dumps([c.to_dict() for c in citations], indent=2)

def get_url(citation_text: str) -> str:
    """Look up a single citation and return its primary URL."""
    cite = lookup(citation_text)
    if cite and cite.sources:
        return cite.sources[0].url
    return ""
```

### As a subprocess

If you can't install jetcite as a dependency, call the CLI:

```python
import subprocess
import json

def find_citations(text: str) -> list[dict]:
    result = subprocess.run(
        ["jetcite", "--scan", "-", "--format", "json"],
        input=text, capture_output=True, text=True
    )
    return json.loads(result.stdout) if result.returncode == 0 else []

def get_url(citation: str) -> str:
    result = subprocess.run(
        ["jetcite", citation],
        capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else ""
```

### Bundling the source

To include jetcite directly in a skill without installing it as a package, copy the `src/jetcite/` directory into your skill and import from it. The library has no runtime dependencies beyond `click` (CLI only) and `httpx` (verification only). The core parsing and URL generation (`scanner.py`, `patterns/`, `sources/`, `models.py`) are pure Python with no external dependencies.

## Using jetcite from an MCP Server

Wrap the API in MCP tool definitions:

```python
from mcp.server.fastmcp import FastMCP
from jetcite import lookup, scan_text

mcp = FastMCP("jetcite")

@mcp.tool()
def citation_lookup(citation: str) -> dict:
    """Look up a legal citation and return its URL and metadata."""
    cite = lookup(citation)
    if cite:
        return cite.to_dict()
    return {"error": f"No match: {citation}"}

@mcp.tool()
def scan_document(text: str) -> list[dict]:
    """Scan text for all legal citations with URLs."""
    return [c.to_dict() for c in scan_text(text)]
```

## Citation Model

Each `Citation` object has:

| Field | Type | Description |
|-------|------|-------------|
| `raw_text` | `str` | Original matched text |
| `cite_type` | `CitationType` | `case`, `statute`, `constitution`, `court_rule`, `regulation` |
| `jurisdiction` | `str` | `"us"`, `"nd"`, `"oh"`, etc. |
| `normalized` | `str` | Canonical Bluebook form |
| `components` | `dict` | Parsed parts (volume, reporter, page, title, section, etc.) |
| `pinpoint` | `str \| None` | Page, paragraph, or subsection pinpoint |
| `sources` | `list[Source]` | Available URLs with name and verification status |
| `parallel_cites` | `list[str]` | Normalized forms of parallel citations (batch mode) |
| `position` | `int` | Character offset in source text |

Each `Source` has:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Source identifier (`"ndcourts"`, `"courtlistener"`, `"govinfo"`, etc.) |
| `url` | `str` | Generated URL |
| `verified` | `bool \| None` | `None` = not checked, `True`/`False` = HTTP result |

## Caching

jetcite includes a local reference cache (`~/refs/`) that stores fetched citation content for offline access and faster lookups.

```bash
# Fetch and cache a citation
jetcite --fetch "2024 ND 156" --refs-dir ~/refs

# Check local cache first, then fall back to web
jetcite --refs-dir ~/refs "2024 ND 156"
jetcite --scan document.md --refs-dir ~/refs
```

Content-type-centric layout:
- `opin/{reporter}/` — all opinions (ND/, NW2d/, US/, F3d/, P2d/, etc.)
- `statute/{code}/` — statutes (NDCC/, USC/)
- `reg/{code}/` — regulations (NDAC/, CFR/)
- `cnst/{jurisdiction}/` — constitutions (ND/, US/)
- `rule/{set}/` — court rules (ndrcivp/, FRCP/, FRE/, etc.)

HTML and PDF content is automatically converted to markdown. Original downloads are preserved as dot-prefixed siblings (e.g., `.351.orig.html`). Metadata sidecars (`.meta.json`) track source URL, fetch time, content hash, ETag, and staleness.

## Supported Citations

### Federal
- U.S. Constitution (articles, amendments)
- U.S. Code (U.S.C.)
- Code of Federal Regulations (C.F.R.)
- Federal rules (FRCP, FRCrP, FRE, FRAP, FRBP)
- All federal case reporters (U.S., S. Ct., F.3d/4th, F. Supp., L. Ed., B.R., etc.)

### State — Regional Reporters
- All seven West regional reporters (N.W.2d, A.3d, S.E.2d, So.3d, S.W.3d, N.E.3d, P.3d)
- State-specific reporters (Cal., N.Y., Ohio St., Wash., Ill.)

### State — Medium-Neutral Citations
- 21 jurisdictions: AR, AZ, CO, GU, IL, ME, MP, MT, NC, ND, NH, NM, OH, OK, PA, PR, SD, UT, VT, WI, WY

### North Dakota (deep coverage)
- N.D.C.C. sections and chapters (with decimal titles like 12.1)
- N.D.A.C. sections and chapters
- N.D. Constitution
- All 21 ND court rule sets
- North Dakota Reports (N.D.) — volumes 1-79, 1890-1953
- Medium-neutral citations (1997-present)

## URL Sources

| Source | URL | Used for |
|--------|-----|----------|
| ndcourts.gov | Direct opinion PDFs, rule links, reporter search | ND opinions, ND rules, NW/NW2d/NW3d lookup |
| ndlegis.gov | PDF links with named destinations | NDCC, NDAC |
| ndconst.org | Article/section URLs | ND Constitution |
| govinfo.gov | USC section links | U.S. Code |
| ecfr.gov | Current CFR section links | C.F.R. |
| constitutioncenter.org | Article and amendment pages | U.S. Constitution |
| law.cornell.edu (LII) | Federal rule pages | FRCP, FRE, etc. |
| supreme.justia.com | Opinion pages | U.S. Reports |
| courtlistener.com | `/c/` citation redirect URLs | All case reporters (fallback) |

## Contributing

On a fresh clone, activate the local pre-push sensitive-content check:

```bash
git config --local core.hooksPath .githooks
```

It scans commits being pushed for likely ND court dockets, confidential-case
captions, and committed binaries. Bypass once with `git push --no-verify`.
