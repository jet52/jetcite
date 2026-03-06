# jetcite - American Legal Citation Parser & Linker

A Python library and CLI tool for parsing American legal citations, generating
URLs to official sources, resolving citations against a local reference cache,
and optionally verifying that sources resolve. Designed for Bluebook-compliant
citations but forgiving of common deviations.

## Goals

- Parse legal citations from text using regex patterns
- Generate URLs to official government sources (preferred) or reliable secondary
  sources
- Provide both single-citation lookup and batch document scanning
- Maintain a local reference cache (`~/refs/`) that builds incrementally as
  citations are fetched — enabling offline access and faster lookups
- Optionally verify that generated URLs resolve (HTTP check)
- Support pinpoint citations (page, paragraph) and pass them through to URL
  anchors where the target site supports it
- Serve as the single citation engine for all projects (jetredline, jetmemo-skill,
  jetbriefcheck, Claude Code skills)
- Start with deep North Dakota coverage, expand to other states incrementally
- Modular architecture: each state/jurisdiction is a pluggable module

## Non-Goals

- Full Bluebook validation or formatting correction
- Comprehensive coverage of every historical reporter variant

---

## Architecture

```
~/code/jetcite/
├── src/jetcite/
│   ├── __init__.py                # Top-level API: lookup(), scan_text()
│   ├── cli.py                     # CLI entry point
│   ├── scanner.py                 # Batch scanning, deduplication, parallel cite detection
│   ├── models.py                  # Citation, CitationType, Source, to_dict()
│   ├── resolver.py                # URL verification + rate limiting
│   ├── cache.py                   # Local reference cache (~/refs/) [planned]
│   ├── patterns/
│   │   ├── __init__.py            # Pattern registry, priority ordering
│   │   ├── base.py                # Base matcher class, helpers
│   │   ├── federal_cases.py       # U.S. Reports, F.3d/4th, F. Supp., S. Ct., etc.
│   │   ├── federal_statutes.py    # U.S.C., C.F.R.
│   │   ├── federal_rules.py       # Fed. R. Civ. P., Fed. R. Evid., etc.
│   │   ├── constitutions.py       # U.S. Const., state constitutions
│   │   ├── regional.py            # Regional reporters (N.W.2d, A.3d, etc.)
│   │   ├── neutral.py             # Medium-neutral citations (2024 ND 156, etc.)
│   │   └── states/
│   │       ├── __init__.py        # State module registry
│   │       ├── nd.py              # North Dakota (NDCC, NDAC, ND court rules)
│   │       └── ...                # Other states added incrementally
│   └── sources/
│       ├── __init__.py            # Source registry
│       ├── courtlistener.py       # CourtListener /c/ URLs for cases
│       ├── constitutioncenter.py  # constitutioncenter.org for U.S. Const.
│       ├── cornell.py             # law.cornell.edu (LII) for federal rules
│       ├── govinfo.py             # govinfo.gov for U.S.C.
│       ├── ecfr.py                # eCFR for C.F.R.
│       ├── justia.py              # Justia for U.S. Reports
│       ├── ndcourts.py            # ndcourts.gov for ND opinions and rules
│       ├── ndlegis.py             # ndlegis.gov for NDCC and NDAC
│       └── ndconst.py             # ndconst.org for ND Constitution
├── tests/
│   ├── test_federal_cases.py
│   ├── test_federal_statutes.py
│   ├── test_constitutions.py
│   ├── test_regional.py
│   ├── test_neutral.py
│   ├── test_nd.py
│   ├── test_scanner.py
│   ├── test_resolver.py
│   └── test_cache.py             # [planned]
├── pyproject.toml
├── PLAN.md
└── README.md
```

### Key Design Decisions

**Pattern registry with priority ordering.** Matchers register at a priority
level. Scanner tries them in order; all matches are collected (not first-match-
wins) so batch mode can find every citation in a document. Individual lookup
mode returns the first match.

**Forgiving regex.** Each pattern has a canonical form and known variants:
- Periods optional in abbreviations: `N.W.2d` matches `NW2d`, `N.W. 2d`
- Section symbol optional: `§` or `section` or bare number after code name
- Flexible whitespace between components
- Smart quotes and unicode equivalents accepted (§, ¶, curly quotes)

**Source modules.** URL generation is separated from pattern matching. A citation
match produces a structured `Citation` object; the resolver looks up the
appropriate source module(s) to generate URLs. Multiple sources can be returned
per citation (e.g., CourtListener + official state site).

**State modules are pluggable.** Each state module registers its patterns
(statutes, admin code, court rules, state-specific reporters) and its URL
sources. Start with ND; add others as needed without touching core code.

**Local reference cache.** Citations can be resolved against a local `~/refs/`
directory before making web requests. Content fetched from the web is cached
locally for future use. The cache is organized by citation type and uses
markdown format so Claude and humans can both read it natively.

---

## Data Model

```python
@dataclass
class Citation:
    raw_text: str              # Original matched text
    cite_type: CitationType    # Enum: case, statute, rule, constitution, regulation
    jurisdiction: str          # "us", "nd", "ca", etc.
    normalized: str            # Canonical Bluebook form
    components: dict           # Parsed parts (volume, reporter, page, title, section, etc.)
    pinpoint: str | None       # Page, paragraph, or subsection pinpoint
    sources: list[Source]      # Available URL sources (local, web)
    position: int              # Character offset in source text
    parallel_cites: list[str]  # Normalized forms of parallel citations

    def to_dict(self) -> dict  # JSON-serializable dictionary

@dataclass
class Source:
    name: str                  # "local", "ndcourts", "courtlistener", "govinfo", etc.
    url: str                   # file:// or https:// URL
    verified: bool | None      # None = not checked, True/False = HTTP result
    anchor: str | None         # URL fragment for pinpoint (if supported)

class CitationType(Enum):
    CASE = "case"
    STATUTE = "statute"
    CONSTITUTION = "constitution"
    COURT_RULE = "court_rule"
    REGULATION = "regulation"
```

---

## CLI Interface

```bash
# Single citation lookup
jetcite "585 N.W.2d 123"
jetcite "N.D.C.C. § 1-02-13"
jetcite --from-clipboard

# Batch mode: scan a document
jetcite --scan document.md
jetcite --scan document.md --format json
cat brief.txt | jetcite --scan -

# Options
jetcite --verify              # HTTP-check each URL
jetcite --format url          # Default: just the URL
jetcite --format json         # Full structured output
jetcite --format table        # Human-readable table
jetcite --open                # Open first URL in browser
jetcite --all-sources         # Show all available URLs, not just primary
jetcite --refs-dir ~/refs     # Check local cache first [planned]
```

### Batch mode output (default: table)

```
  #  Citation              Type      URL
  1  2024 ND 156           case      https://www.ndcourts.gov/supreme-court/opinion/2024ND156
                                     = 10 N.W.3d 500
  2  N.D.C.C. § 1-02-13   statute   https://ndlegis.gov/cencode/t01c02.pdf#nameddest=1-2-13
  3  585 N.W.2d 123        case      https://www.ndcourts.gov/supreme-court/opinions?cit1=585&citType=NW2d&cit2=123...
```

---

## Citation Patterns

### Priority 1: Constitutions

#### U.S. Constitution
- **Canonical:** `U.S. Const. art. III, § 2` / `U.S. Const. amend. XIV`
- **Forgiving:** `US Const`, `United States Constitution`, `U.S. Constitution`
- **Components:** article or amendment (Roman numeral), optional section, optional clause
- **Source:** constitutioncenter.org (articles and amendments have defined URL paths)

#### State Constitutions (starting with ND)
- **Canonical:** `N.D. Const. art. I, § 20`
- **Forgiving:** `ND Const`, `North Dakota Constitution`
- **Components:** article (Roman), section
- **Source:** ndconst.org — `https://ndconst.org/art{roman}/sec{num}/`

### Priority 2: Federal Statutes

#### United States Code
- **Canonical:** `42 U.S.C. § 1983`
- **Forgiving:** `42 USC § 1983`, `42 USC 1983`, `42 U.S.C. §§ 1983-1985`
- **Components:** title, section, optional subsection
- **Source:** govinfo.gov — `https://www.govinfo.gov/link/uscode/{title}/{section}?link-type=html`

#### Code of Federal Regulations
- **Canonical:** `29 C.F.R. § 1910.1200`
- **Forgiving:** `29 CFR 1910.1200`, `29 C.F.R. § 1910.1200(a)(2)`
- **Components:** title, section (may include decimals), optional subsection
- **Source:** ecfr.gov — `https://www.ecfr.gov/current/title-{title}/section-{section}`

### Priority 3: Federal Rules

| Rule Set | Canonical | Abbreviation |
|----------|-----------|-------------|
| Civil Procedure | Fed. R. Civ. P. 12(b)(6) | FRCP |
| Criminal Procedure | Fed. R. Crim. P. 29 | FRCrP |
| Evidence | Fed. R. Evid. 801 | FRE |
| Appellate Procedure | Fed. R. App. P. 28 | FRAP |
| Bankruptcy Procedure | Fed. R. Bankr. P. 7001 | FRBP |

- **Forgiving:** `FRCP 12(b)(6)`, `Rule 12(b)(6), Fed. R. Civ. P.`
- **Source:** law.cornell.edu (LII) — structured URLs per rule set

### Priority 4: State Statutes and Rules (modular per state)

#### North Dakota (first module)

**N.D.C.C. (Century Code)**
- **Canonical:** `N.D.C.C. § 12.1-32-01`
- **Forgiving:** `NDCC § 12.1-32-01`, `NDCC 12.1-32-01`, `§ 12.1-32-01, N.D.C.C.`
- **Components:** title (with optional decimal), chapter, section (with optional decimal)
- **Sources:**
  - ndlegis.gov — `https://ndlegis.gov/cencode/t{title}c{chapter}.pdf#nameddest={title}-{chapter}-{section}`

**N.D.A.C. (Admin Code)**
- **Canonical:** `N.D.A.C. § 43-02-05-01`
- **Forgiving:** `NDAC § 43-02-05-01`, `N.D. Admin. Code § 43-02-05-01`
- **Components:** 3-part chapter (title-article-chapter), optional 4th part (section)
- **Source:** ndlegis.gov — `https://ndlegis.gov/information/acdata/pdf/{p1}-{p2}-{p3}.pdf`

**ND Court Rules** (21 rule sets)
- N.D.R.Civ.P., N.D.R.Crim.P., N.D.R.App.P., N.D.R.Ev., N.D.R.Ct.,
  N.D. Sup. Ct. Admin. R., N.D.R. Prof. Conduct, N.D.R. Lawyer Discipl.,
  N.D. Code Jud. Conduct, N.D.R. Juv. P., N.D.R. Continuing Legal Ed.,
  N.D. Admission to Practice R., N.D. Stds. Imposing Lawyer Sanctions,
  N.D.R. Proc. R., N.D.R. Local Ct. P.R., N.D. Student Practice R.,
  N.D.R. Jud. Conduct Commission, Local Rules
- **Source:** ndcourts.gov — `https://www.ndcourts.gov/legal-resources/rules/{ruleSet}/{parts}`

### Priority 5: Medium-Neutral State Case Citations

States with adopted medium-neutral formats (from Indigo Book T3):

| State | Format | Example | Effective |
|-------|--------|---------|-----------|
| Arkansas | YYYY Ark. NNN | 2017 Ark. App. 605 | 2009 |
| Colorado | YYYY CO NNN | 2019 CO 44 | 2012 |
| Guam | YYYY Guam NNN | 1997 Guam 4 | — |
| Illinois | YYYY IL NNNNNN | 2011 IL 102345 | 2011 |
| Louisiana | NN-NNNN (La. date) | 93-2345 (La. 7/15/94) | 1994 |
| Maine | YYYY ME NNN | 2011 ME 24 | 1997 |
| Mississippi | YYYY-CC-NNNNN-SCT | 2017-CA-01472-SCT | 1997 |
| Montana | YYYY MT NNN | 1998 MT 12 | 1998 |
| N. Mariana Is. | YYYY MP NNN | 2001 MP 1 | — |
| New Mexico | YYYY-NMSC-NNN | 2012-NMSC-012 | 2013 |
| North Carolina | YYYY-NCSC-NNN | 2021-NCSC-57 | 2021 |
| North Dakota | YYYY ND NNN | 1997 ND 15 | 1997 |
| Ohio | YYYY-Ohio-NNNN | 2002-Ohio-2220 | 2002 |
| Oklahoma | YYYY OK NNN | 2006 OK 24 | 1997 |
| Pennsylvania | YYYY PA Super NNN | 1999 PA Super 1 | 1999 |
| Puerto Rico | YYYY TSPR NNN | 2015 TSPR 148 | 1998 |
| South Dakota | YYYY S.D. NNN | 2013 S.D. 54 | 1997 |
| Utah | YYYY UT NNN | 1999 UT 16 | 1999 |
| Vermont | YYYY VT NNN | 2001 VT 1 | 2003 |
| Wisconsin | YYYY WI NNN | 2000 WI 14 | 2000 |
| Wyoming | YYYY WY NNN | 2001 WY 12 | 2004 |

**Source priority for medium-neutral citations:**
1. Official state court website (if URL is constructable)
2. CourtListener — `https://www.courtlistener.com/c/{jurisdiction}/{year}/{number}/`

### Priority 6: Regional Reporters (Case Citations)

All regional reporters from the West National Reporter System:

| Reporter | Abbreviation(s) | Region |
|----------|-----------------|--------|
| Atlantic | A., A.2d, A.3d | CT, DE, DC, ME, MD, NH, NJ, PA, RI, VT |
| North Eastern | N.E., N.E.2d, N.E.3d | IL, IN, MA, NY, OH |
| North Western | N.W., N.W.2d | IA, MI, MN, NE, ND, SD, WI |
| Pacific | P., P.2d, P.3d | AK, AZ, CA, CO, HI, ID, KS, MT, NV, NM, OK, OR, UT, WA, WY |
| South Eastern | S.E., S.E.2d | GA, NC, SC, VA, WV |
| Southern | So., So. 2d, So. 3d | AL, FL, LA, MS |
| South Western | S.W., S.W.2d, S.W.3d | AR, KY, MO, TN, TX |

**Pattern:** `{volume} {reporter} {page}`
- **Forgiving:** periods optional (`NW2d` = `N.W.2d`), flexible spacing
- NW/NW2d/NW3d get ndcourts.gov search URL as primary source

**State-specific reporters** (selected high-volume):

| Reporter | Abbreviation(s) |
|----------|-----------------|
| North Dakota | N.D. (vols 1-79, 1890-1953) |
| California | Cal., Cal. 2d, Cal. 3d, Cal. 4th, Cal. 5th |
| California Reporter | Cal. Rptr., Cal. Rptr. 2d, Cal. Rptr. 3d |
| New York | N.Y., N.Y.2d, N.Y.3d |
| New York Supplement | N.Y.S., N.Y.S.2d, N.Y.S.3d |
| Ohio State | Ohio St., Ohio St. 2d, Ohio St. 3d |
| Illinois | Ill., Ill. 2d |
| Illinois Decisions | Ill. Dec. |
| Washington | Wash., Wash. 2d |
| Washington App. | Wash. App., Wash. App. 2d |

**Source:** CourtListener — `https://www.courtlistener.com/c/{reporter}/{volume}/{page}/`

### Priority 7: Federal Case Reporters

| Reporter | Abbreviation(s) | Court Level |
|----------|-----------------|-------------|
| United States Reports | U.S. | Supreme Court |
| Supreme Court Reporter | S. Ct. | Supreme Court |
| Lawyers' Edition | L. Ed., L. Ed. 2d | Supreme Court |
| Federal Reporter | F., F.2d, F.3d, F.4th | Circuit Courts |
| Federal Appendix | F. App'x | Circuit Courts (unpub.) |
| Federal Supplement | F. Supp., F. Supp. 2d, F. Supp. 3d | District Courts |
| Federal Rules Decisions | F.R.D. | District Courts |
| Bankruptcy Reporter | B.R. | Bankruptcy Courts |
| Federal Claims | Fed. Cl. | Court of Federal Claims |
| Military Justice | M.J. | Armed Forces Courts |
| Veterans Appeals | Vet. App. | Veterans Claims |
| Tax Court | T.C. | Tax Court |

**Pattern:** `{volume} {reporter} {page}`

**Sources:**
- U.S. Reports → Justia: `https://supreme.justia.com/cases/federal/us/{volume}/{page}`
- S. Ct. → CourtListener
- All others → CourtListener: `https://www.courtlistener.com/c/{reporter}/{vol}/{page}/`

---

## Pinpoint Handling

Citations often include pinpoints after the base citation:
- **Page:** `585 N.W.2d 123, 128` or `585 N.W.2d 123 at 128`
- **Paragraph:** `2024 ND 156, ¶ 12` or `2024 ND 156 at ¶¶ 12-15`
- **Subsection:** `42 U.S.C. § 1983(1)` (captured as part of section)

The parser captures pinpoints as a separate field in the `Citation` object. The
resolver passes pinpoints through to URL anchors where the target site supports
them:
- ndcourts.gov opinion pages don't have paragraph anchors (pinpoint informational only)
- ndlegis.gov PDFs support `#nameddest=` anchors for NDCC sections
- Some future sources may support page-level anchors

---

## Parallel Citation Detection

When two case citations appear adjacent in text separated by a comma or
semicolon (e.g., `2024 ND 156, 10 N.W.3d 500`), they refer to the same case.
The scanner detects these and:
- Links them via each citation's `parallel_cites` list
- Merges their sources so each citation has access to both URLs
- Handles pinpoints between parallel cites (e.g., `2024 ND 156, ¶ 12, 10 N.W.3d 500`)
- Rejects false positives by checking for sentence boundaries and non-citation text

---

## Verification Mode

When `--verify` is passed:
1. For each citation, verify the primary (non-CourtListener) source URL
2. Issue an HTTP HEAD request, accept 200 or 3xx as verified
3. Skip CourtListener `/c/` redirect URLs when an alternative source exists
4. Cache verification results to avoid re-checking shared URLs across parallel cites
5. Rate-limit requests (1 req/sec default, configurable)
6. Report verification results in output

Uses `httpx` for async HTTP. Verification is always optional — the tool works
fully offline for URL generation.

**CourtListener best practices:** The `/c/` URLs are lightweight browser-facing
redirect links. For programmatic verification, CourtListener's Citation Lookup
API is preferred:
```
POST https://www.courtlistener.com/api/rest/v4/citation-lookup/
(requires auth token, 60 citations/min, 250 per request)
```

---

## URL Sources Reference

### Official Government Sources (preferred)

| Source | Base URL | Citation Types |
|--------|----------|---------------|
| govinfo.gov | `https://www.govinfo.gov/link/uscode/{title}/{section}` | U.S.C. |
| ecfr.gov | `https://www.ecfr.gov/current/title-{title}/section-{section}` | C.F.R. |
| constitutioncenter.org | `https://constitutioncenter.org/the-constitution/...` | U.S. Const. |
| ndcourts.gov | `https://www.ndcourts.gov/...` | ND opinions, ND rules, NW reporter search |
| ndlegis.gov | `https://ndlegis.gov/cencode/...` | NDCC, NDAC |
| ndconst.org | `https://ndconst.org/art.../sec.../` | ND Const. |

### Secondary Sources

| Source | Base URL | Citation Types |
|--------|----------|---------------|
| CourtListener | `https://www.courtlistener.com/c/{reporter}/{vol}/{page}/` | All case reporters |
| Justia | `https://supreme.justia.com/cases/federal/us/{vol}/{page}` | U.S. Reports |
| LII (Cornell) | `https://www.law.cornell.edu/rules/...` | Federal rules |

### Adding Sources for New States

When a new state module is added, the implementer should research:
1. **Official court website** — can URLs be constructed from neutral citations?
2. **Official legislature website** — can statute URLs be constructed from
   title/chapter/section?
3. **CourtListener coverage** — does `/c/{reporter}/{vol}/{page}/` work for this
   state's reporters?

---

## Implementation Plan

### Phase 1: Core Framework + ND (MVP) — COMPLETE (v0.1.0)

1. ~~Project setup~~ — pyproject.toml, CLI entry point, dependencies
2. ~~Data model~~ — Citation, Source, CitationType dataclasses, to_dict()
3. ~~Pattern framework~~ — Base matcher, registry, priority ordering
4. ~~Federal patterns~~ — U.S. Constitution, U.S.C., C.F.R., federal rules,
   all federal case reporters, all regional reporters
5. ~~Medium-neutral citations~~ — 21 jurisdictions
6. ~~North Dakota module~~ — NDCC, NDAC, ND Constitution, 21 court rule sets
7. ~~Resolver~~ — URL generation, optional HTTP verification
8. ~~Scanner~~ — Batch scanning, deduplication, position tracking
9. ~~CLI~~ — Single and batch modes, url/json/table output, all flags
10. ~~Tests~~ — 56 tests passing

### Phase 1.5: Parallel Citations + ND History — COMPLETE (v0.2.0)

1. ~~Parallel citation detection~~ — detect adjacent case citations, link and
   merge sources
2. ~~North Dakota Reports~~ — N.D. state reporter (vols 1-79, 1890-1953)
3. ~~ndcourts.gov reporter search~~ — search URL for NW/NW2d/NW3d citations
4. ~~CourtListener best practices~~ — skip /c/ URLs in verify mode, cache
   verified URLs, document API

### Phase 1.6: API + Documentation — COMPLETE (v0.3.0)

1. ~~Top-level API~~ — `from jetcite import lookup, scan_text`
2. ~~Citation.to_dict()~~ — JSON serialization
3. ~~Cross-platform clipboard~~ — pyperclip instead of pbpaste
4. ~~README~~ — CLI usage, Python API, skill/plugin integration, MCP example

### Phase 2: Local Reference Cache

Add local file resolution and incremental caching to `~/refs/`.

1. **Cache module** (cache.py)
   - `resolve_local(citation, refs_dir) -> Path | None` — map a Citation to
     its local file path based on citation type and components
   - `cache_content(citation, content, refs_dir)` — write fetched content to
     the refs directory in markdown format
   - `fetch_and_cache(citation, refs_dir) -> str` — download from primary web
     source, cache locally, return content

2. **Cache directory structure** (matches existing ~/refs/ layout)
   ```
   ~/refs/
   ├── opin/markdown/{year}/{year}ND{number}.md    # ND opinions
   ├── ndcc/title-{n}/chapter-{n}-{ch}.md          # NDCC chapters
   ├── ndac/title-{n}/article-{n}-{a}/chapter-{n}-{a}-{ch}.md
   ├── cnst/art-{nn}/sec-{n}.md                    # ND Constitution
   ├── rule/{ruleset}/rule-{parts}.md               # Court rules
   └── federal/
       ├── usc/{title}/{section}.md                 # U.S. Code sections
       └── opinions/{reporter}/{volume}/{page}.md   # Federal cases
   ```

3. **Cache metadata** — `.meta.json` sidecar files alongside cached content:
   ```json
   {
     "source_url": "https://www.ndcourts.gov/...",
     "fetched": "2026-03-06T12:00:00Z",
     "citation": "2024 ND 156",
     "content_type": "text/html"
   }
   ```

4. **Staleness policy**
   - Opinions: permanent (immutable once published)
   - Constitutions: permanent (amendments are new sections, not edits)
   - Statutes and regulations: stale after 90 days (legislative sessions)
   - Court rules: stale after 180 days
   - Staleness = informational warning, not auto-refetch

5. **Integration with lookup/scan_text**
   - Add optional `refs_dir` parameter to `lookup()` and `scan_text()`
   - When set, check local cache first; add `Source(name="local",
     url="file:///...")` at top of sources list if found
   - `search_hint` field on Citation for finding content within cached files

6. **CLI integration**
   - `jetcite --refs-dir ~/refs "2024 ND 156"` — check local first
   - `jetcite --scan doc.md --refs-dir ~/refs` — report cache hits vs misses
   - `jetcite --fetch "2024 ND 156" --refs-dir ~/refs` — fetch and cache

7. **Tests** for cache resolution, caching, staleness detection

### Phase 3: Expand State Coverage

Add state modules as needed. Priority candidates:
- Minnesota (8th Circuit neighbor, N.W.2d)
- South Dakota (8th Circuit neighbor, N.W.2d)
- Montana (similar rural western state, medium-neutral)
- Any state that comes up in a specific case or project

Each state module adds:
- State statute regex + URL builder
- State admin code regex + URL builder (if applicable)
- State court rule regex + URL builder (if applicable)
- State constitution regex + URL builder

### Phase 4: Enhanced Features

- **Id. citation tracking** — resolve `Id.` and `Id. at 128` to the preceding
  citation in batch mode (see Future Enhancements below)
- **Short-form citation resolution** — e.g., `Smith, 585 N.W.2d at 128`
  resolved against earlier full citation in the same document
- **Citation normalization** — convert informal citations to Bluebook form
- **Export formats** — Markdown with hyperlinks, HTML

### Phase 5: MCP Server

Run jetcite as a single MCP server that all tools connect to.

1. **MCP server module** (mcp_server.py)
   - `citation_lookup` tool — parse single citation, return dict
   - `scan_document` tool — batch scan, return list of dicts
   - `fetch_citation` tool — fetch content and cache locally

2. **Shared state** — one refs cache, one set of rate limits, one place to
   update patterns. jetredline, jetmemo-skill, jetbriefcheck, and Claude Code
   all use the same server.

3. **Cache statistics** — report cache hits/misses, staleness warnings

---

## Future Enhancements

### Id. Citation Support (Batch Mode)

In legal writing, `Id.` (or `id.`) refers to the immediately preceding citation.
`Id. at 128` refers to the preceding citation at page 128. In batch mode,
jetcite should:

1. Track citation state: maintain a "last citation" reference as the scanner
   moves through the document
2. When encountering `Id.` or `Id. at {pinpoint}`:
   - Resolve it to the preceding citation
   - Generate the same URL, potentially with a different pinpoint anchor
   - Output the resolved citation in results with a note that it was an Id. reference
3. Handle `Id.` at paragraph boundaries — only valid within the same footnote
   or text paragraph in most styles, but this level of context-awareness may be
   hard to implement perfectly. Start with simple "last citation" tracking and
   document the limitation.

### Other Future Features

- **Supra/infra support** — resolve references to earlier/later citations in
  the same document
- **CourtListener API integration** — use the citation-lookup API for richer
  case metadata (case name, date, court). Requires auth token.
- **Short-form citation resolution** — e.g., `Smith, 585 N.W.2d at 128`
  resolved against earlier full citation

---

## Dependencies

### Runtime
- `click` — CLI framework
- `httpx` — async HTTP for verification mode

### Optional
- `pyperclip` — cross-platform clipboard support (`pip install jetcite[clipboard]`)

### Development
- `pytest` — testing
- `ruff` — linting and formatting

### No dependency on
- Any PDF library (consuming projects handle their own document formats)
- Any AI/LLM library (pure regex parsing)
- Any database (stateless operation)

---

## Deprecated Projects

### cite2url (Swift) — ARCHIVED

**Status:** Superseded by jetcite. All regex patterns and URL builders have been
ported to Python.

**Repository:** `~/code/cite2url/` → archive on GitHub

**What it did:** Swift CLI tool for single-citation-to-URL lookup. 50+ citation
patterns, 14 URL builders, macOS Automator integration.

**Why deprecated:** jetcite provides a strict superset — all the same patterns
plus batch scanning, parallel citation detection, multiple sources, HTTP
verification, Python library API, and cross-platform support. The Swift codebase
is harder to maintain and can't be imported by Python projects.

**Migration:** No migration needed. Replace `cite2url "citation"` with
`jetcite "citation"` in any scripts or Automator actions.

### cite-linker-pro (XML regex) — ARCHIVED

**Status:** Superseded by jetcite.

**Repository:** `~/code/cite-linker-pro/` → archive on GitHub

**What it did:** XML-based regex pattern collection for citation linking. ~100+
patterns for ND, federal, and regional citations with CourtListener and ndlegis
URL generation.

**Why deprecated:** jetcite implements the same patterns in Python with a proper
registry, priority ordering, and test coverage. XML regex patterns are harder to
debug and test than Python code.

---

## Porting Notes

### From cite2url (Swift) — COMPLETE

All patterns and URL builders ported:
- ~~21 ND court rule patterns~~
- ~~NDCC section/chapter patterns~~
- ~~NDAC patterns~~
- ~~ND Constitution patterns~~
- ~~US Constitution patterns~~
- ~~Federal statute patterns~~
- ~~All state case patterns — regional + neutral + state-specific~~
- ~~All federal reporter patterns~~
- ~~URL generation logic — 14 URL builder functions~~

### From jetredline (nd_cite_check.py) — PARTIAL

Ported:
- ~~Forgiving regex variants (flexible periods/spacing)~~
- ~~Parallel citation detection~~
- ~~Deduplication logic~~
- ~~Citation record structure~~

Remaining (Phase 2):
- Local file resolution logic (`resolve_local()`)
- Search hints for locating text within cached files
- Integration: replace nd_cite_check.py's ~800 lines of regex with
  `from jetcite import scan_text`

### From jetmemo-skill (verify_citations.py) — PARTIAL

Ported:
- ~~Rate limiting approach~~

Remaining (Phase 2):
- Multi-source verification chain (local → web → API)
- CourtListener API interaction (citation-lookup endpoint)

---

## Integration Roadmap

After Phase 2 (local reference cache) is complete, update these projects to
use jetcite as their citation engine:

### jetredline — nd_cite_check.py
- Replace ~800 lines of regex patterns with `from jetcite import scan_text`
- Keep the thin wrapper that calls `scan_text()` with `refs_dir=~/refs`
- Preserve the CLI interface (`--file`, `--refs-dir`) and JSON output schema
  expected by SKILL.md Pass 3B
- Add `search_hint` to jetcite output so the subagent knows what to grep for

### jetmemo-skill — verify_citations.py
- Replace citation extraction with `from jetcite import scan_text`
- Use jetcite's local cache resolution instead of custom `verify_local()`
- Use jetcite's fetch_and_cache for web fallback
- Keep the agent-specific verification chain (Agent D/E prompts)

### jetbriefcheck
- Import jetcite for citation extraction in mechanical/semantic checks
- Lower priority — citation checking is peripheral to brief compliance

### Claude Code / Claude Cowork
- Use jetcite as an MCP server (Phase 5) or as a skill dependency
- Incrementally build ~/refs/ cache during bench memo and opinion work
- Each case worked adds its citations to the local cache automatically
