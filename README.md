# jetcite

American legal citation parser and linker. Parses legal citations from text, generates URLs to official government sources or reliable aggregators like courtlistener.com, and optionally verifies that URLs resolve.

## Not an Official Court Product

jetcite is an independent, open-source project published by an individual in a
personal capacity as legal-educational software, consistent with Rule 3.1 of the
North Dakota Code of Judicial Conduct. It is not authorized, endorsed, or maintained
by the North Dakota Supreme Court or any court. Parsed citations and generated links
are machine-generated and may be inaccurate or incomplete — verify against the
official source before relying on them. It is not legal advice.

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

### Network egress in sandboxed environments (Claude Cowork / Claude Code)

Citation *parsing* and URL *generation* are fully offline. But a few features
make outbound HTTP requests, and sandboxed Claude environments route all egress
through a filtering proxy with a domain allowlist. If the target host is not on
the allowlist, the request is rejected at the proxy (HTTP 403 on CONNECT) and
jetcite degrades silently to a less specific result.

The feature most users notice: by default a scan resolves each ND opinion's
search URL to the **direct opinion PDF URL** (e.g.
`…/supreme-court/opinions/114404`) by fetching `www.ndcourts.gov`. With that host
blocked, the citation keeps the one-click-away *search* URL
(`…/opinions?cit1=2008&citType=ND&cit2=144…`) instead. (jetcite also works with
no `httpx` installed — it falls back to the standard-library `urllib`, which uses
the same proxy.)

**To allowlist the domains in Claude Cowork:** open the sandbox settings →
**Allow network egress** → **Domain allowlist** → **Additional allowed domains**,
and add the hosts below. In local Claude Code, set the same hosts under
`sandbox.network.allowedDomains` in `.claude/settings.json`.

Two things that commonly trip people up:

- **A bare domain does not match its subdomains.** jetcite requests
  `www.ndcourts.gov`, so an allowlist entry of `ndcourts.gov` alone will still
  403. Use the wildcard `*.ndcourts.gov` (or list the exact host
  `www.ndcourts.gov`).
- **The allowlist is read when the session starts.** Editing it does not
  reconfigure an already-running sandbox — start a **new** session after
  changing it.

Recommended entries (the canonical list lives in
[`src/jetcite/NETWORK.md`](src/jetcite/NETWORK.md), which ships with every
vendored copy):

| Allowlist entry | Enables |
|-----------------|---------|
| `*.ndcourts.gov` | Direct ND opinion PDF URLs (default scan behavior); ND rule and case-record links |
| `www.courtlistener.com` | Case-law fallback URLs and source verification |
| `supreme.justia.com` | U.S. Reports opinion pages |
| `www.law.cornell.edu` | Federal rule pages (FRCP, FRE, etc.) |
| `www.govinfo.gov` | U.S. Code section links |
| `www.ecfr.gov` | C.F.R. section links |
| `ndlegis.gov` | NDCC, NDAC |
| `ndconst.org` | ND Constitution |
| `constitution.congress.gov` | U.S. Constitution (Constitution Annotated, Library of Congress — official) |
| `constitutioncenter.org` | U.S. Constitution |

This list is enforced by `tests/test_egress.py`: if a future source module adds
a new host, the test fails until the host is added to `EGRESS_ALLOWLIST` and to
both this table and `NETWORK.md`.

At minimum, add `*.ndcourts.gov` — it is the only host needed for the default
ND opinion PDF resolution. To verify the allowlist took effect, run a lookup in a
fresh session and confirm you get a `…/opinions/<id>` URL rather than a
`…/opinions?cit1=…` search URL:

```bash
python3 path/to/jetcite_tool.py lookup "2008 ND 144"
# → https://www.ndcourts.gov/supreme-court/opinions/114404
```

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
| `antecedent_name` | `str \| None` | Best-effort case name governing the cite, e.g. `"Boedecker v. St. Alexius Hospital"` (heuristic; `None` when no name is found — see note below) |
| `improper_parallel_pincite` | `bool` | ND style defect: this reporter cite is the parallel half of a ND public-domain pair *and* carries a page pin cite (batch mode; see note below) |

> **`improper_parallel_pincite`** implements a rule from the North Dakota Supreme Court's supplement to the Redbook (`reference/nd-citation-style.md`): a full public-domain cite gives the North Western Reporter's **first page only**, because the ¶ is the pinpoint and appears in both sources. So `1997 ND 231, ¶ 10, 571 N.W.2d 358, 360` is improper and `…, 571 N.W.2d 358` is correct. The flag is deliberately scoped to ND pairs — other states' medium-neutral conventions are not jetcite's to assert — and is never raised for a pre-1997 ND cite (`512 N.W.2d 470, 477 (N.D. 1994)`), where the reporter pin cite *is* the correct form.
>
> **North Dakota Court of Appeals** cites normalize as `YYYY ND App N`, carry `components["court"] == "ND App"`, resolve through `citType=NDApp` on ndcourts.gov, and cache under `opin/NDApp/`. They share a year/number space with Supreme Court cites — `2005 ND 7` and `2005 ND App 7` are different cases — so never drop the `App` token.

> **`antecedent_name` is a heuristic**, unlike the deterministic fields above. It is recovered by looking back from the citation into the surrounding prose for a `X v. Y` / `In re X` caption, so the left boundary is inherently fuzzy. Treat it as a hint (useful for disambiguating a reporter page shared by more than one case), tolerate `None`, and prefer full `v.` captions over short-form matches. The standalone helper `extract_antecedent_name(text, position)` is also exported.

Each `Source` has:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Source identifier (`"ndcourts"`, `"courtlistener"`, `"govinfo"`, etc.) |
| `url` | `str` | Generated URL |
| `verified` | `bool \| None` | `None` = not checked, `True`/`False` = HTTP result |

## Short Forms (`include_pin_cites`)

Off by default — `scan_text(text, include_pin_cites=True)` (CLI: `--pin-cites`)
adds Bluebook short forms, each linked to the full cite it refers to. Existing
consumers see byte-identical output without the flag.

| Field | Type | Description |
|-------|------|-------------|
| `is_pin_cite` | `bool` | This citation is a short form |
| `parent_normalized` | `str \| None` | The full cite it refers to; `None` when explicit pin syntax was found but no antecedent resolved (kept as a warning) |
| `pin_page` / `pin_paragraph` | `str \| None` | The pinpoint the short form carries |
| `components["shape"]` | `str` | `reporter_pin` (`491 F.3d at 363`), `name_pin` (`Goss at 365`), `id` (`Id. at 78`), or `rule_pin` (`Rule 27(a)`) |

Short forms inherit their parent's sources and never get their own `~/refs`
files. Unresolvable bare names are dropped rather than guessed.

**Rule short forms carry their attribution rung.** A bare `Rule 27(a)` names no
rule set, so jetcite attributes one by a ladder and records which rung fired in
`components["attribution"]`. Consumers should filter on it — the rungs are not
equally trustworthy:

| Rung | Evidence | Use |
|---|---|---|
| `trailing` | The set is named in the same citation — "Rule 27(a) of the North Dakota Rules of Appellate Procedure" | Nothing inferred |
| `sole_set` | The document's own full cites use this rule number under exactly one set | Document-internal, no corpus needed |
| `marker` | The nearest rule-set mention *anywhere* earlier, unlimited lookback | A guess about scope — in an opinion discussing two rule sets it is wrong often enough that it does not belong in a citation graph |

`cite_type` is `COURT_RULE` for rule short forms (unlike case short forms, which
stay `CASE`), so consumer cache loops treat them correctly. A rule short form
whose set is attributed but which no full cite in the document matches gets a
`parent_normalized` synthesized from set + number — and only when the
attribution is explicit or uncontradicted; a `marker` attribution that conflicts
with the document's own full cites is dropped instead.

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
- State-specific reporters (Ariz., Cal., N.Y., Ohio St., Wash., Ill.)

### State — Medium-Neutral Citations
- 20 jurisdictions: AR, CO, GU, IL, ME, MP, MT, NC, ND, NH, NM, OH, OK, PA, PR, SD, UT, VT, WI, WY

### North Dakota (deep coverage)
- N.D.C.C. sections and chapters (with decimal titles like 12.1)
- N.D.A.C. sections and chapters
- N.D. Constitution
- All 21 ND court rule sets
- North Dakota Reports (N.D.) — volumes 1-79, 1890-1953
- Medium-neutral citations (1997-present)

### Arizona
- A.R.S. statutes (section-level deep links to azleg.gov, incl. decimal sections)
- A.A.C. administrative code (chapter-level PDF on apps.azsos.gov)
- Arizona Constitution (section-level, incl. Article 4 Parts)
- Court rules (recognized; linked to the official azcourts.gov rules index — no
  citation-derivable per-rule URL exists)
- Opinions via Pacific Reporter / Ariz. Reports → courtlistener.com

### Iowa
- Iowa Code (section-level deep links to legis.iowa.gov; chapter-only supported)
- Iowa Administrative Code (rule-level PDF on legis.iowa.gov)
- Iowa Court Rules (whole-chapter PDF on legis.iowa.gov)
- Iowa Constitution (official codified whole-document PDF)
- Opinions via N.W.2d → courtlistener.com

## URL Sources

| Source | URL | Used for |
|--------|-----|----------|
| ndcourts.gov | Direct opinion PDFs, rule links, reporter search | ND opinions, ND rules, NW/NW2d/NW3d lookup |
| ndlegis.gov | PDF links with named destinations | NDCC, NDAC |
| ndconst.org | Article/section URLs | ND Constitution |
| www.azleg.gov | Section and article/section pages | A.R.S., Ariz. Constitution |
| apps.azsos.gov | Chapter PDFs | A.A.C. |
| www.azcourts.gov | Rules index page | Arizona court rules |
| www.legis.iowa.gov | Section/rule/chapter PDFs | Iowa Code, Iowa Admin. Code, Iowa Court Rules, Iowa Constitution |
| govinfo.gov | USC section links | U.S. Code |
| ecfr.gov | Current CFR section links | C.F.R. |
| constitution.congress.gov | Article and amendment pages (official, link-out) | U.S. Constitution |
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
