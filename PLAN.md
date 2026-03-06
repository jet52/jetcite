# jetcite - American Legal Citation Parser & Linker

A Python library and CLI tool for parsing American legal citations, generating
URLs to official sources, and optionally verifying that sources resolve. Designed
for Bluebook-compliant citations but forgiving of common deviations.

## Goals

- Parse legal citations from text using regex patterns
- Generate URLs to official government sources (preferred) or reliable secondary
  sources
- Provide both single-citation lookup (like cite2url) and batch document scanning
  (like jetredline's nd_cite_check.py)
- Optionally verify that generated URLs resolve (HTTP check)
- Support pinpoint citations (page, paragraph) and pass them through to URL
  anchors where the target site supports it
- Start with deep North Dakota coverage, expand to other states incrementally
- Modular architecture: each state/jurisdiction is a pluggable module

## Non-Goals

- Local file resolution (consuming projects handle their own local lookups)
- Full Bluebook validation or formatting correction
- Comprehensive coverage of every historical reporter variant

---

## Architecture

```
~/code/jetcite/
├── src/jetcite/
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point
│   ├── scanner.py              # Batch document scanning, deduplication
│   ├── models.py               # Citation, CitationType, MatchResult dataclasses
│   ├── resolver.py             # URL generation dispatch + optional verification
│   ├── patterns/
│   │   ├── __init__.py         # Pattern registry, priority ordering
│   │   ├── base.py             # Base matcher class, helpers
│   │   ├── federal_cases.py    # U.S. Reports, F.3d/4th, F. Supp., S. Ct., etc.
│   │   ├── federal_statutes.py # U.S.C., C.F.R.
│   │   ├── federal_rules.py    # Fed. R. Civ. P., Fed. R. Evid., etc.
│   │   ├── constitutions.py    # U.S. Const., state constitutions
│   │   ├── regional.py         # Regional reporters (N.W.2d, A.3d, S.E.2d, etc.)
│   │   ├── neutral.py          # Medium-neutral citations (2024 ND 156, etc.)
│   │   └── states/
│   │       ├── __init__.py     # State module registry
│   │       ├── nd.py           # North Dakota (NDCC, NDAC, ND court rules)
│   │       └── ...             # Other states added incrementally
│   └── sources/
│       ├── __init__.py         # Source registry
│       ├── courtlistener.py    # CourtListener /c/ URLs for cases
│       ├── govinfo.py          # govinfo.gov for U.S.C.
│       ├── ecfr.py             # eCFR for C.F.R.
│       ├── justia.py           # Justia for U.S. Reports
│       ├── ndcourts.py         # ndcourts.gov for ND opinions and rules
│       ├── ndlegis.py          # ndlegis.gov for NDCC and NDAC
│       └── generic.py          # Fallback URL builders
├── tests/
│   ├── test_federal_cases.py
│   ├── test_federal_statutes.py
│   ├── test_constitutions.py
│   ├── test_regional.py
│   ├── test_neutral.py
│   ├── test_nd.py
│   ├── test_scanner.py
│   └── test_resolver.py
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
    sources: list[Source]      # Available URL sources

@dataclass
class Source:
    name: str                  # "courtlistener", "govinfo", "ndcourts", etc.
    url: str                   # Generated URL
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
# Single citation lookup (like cite2url)
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
```

### Batch mode output (default: table)

```
  #  Citation              Type      URL
  1  2024 ND 156           case      https://www.ndcourts.gov/supreme-court/opinion/2024ND156
  2  N.D.C.C. § 1-02-13   statute   https://ndlegis.gov/cencode/t01c02.pdf#nameddest=1-2-13
  3  585 N.W.2d 123        case      https://www.courtlistener.com/c/N.W.2d/585/123/
```

### Batch mode output (--format json)

```json
[
  {
    "raw_text": "2024 ND 156, ¶ 12",
    "cite_type": "case",
    "jurisdiction": "nd",
    "normalized": "2024 ND 156",
    "pinpoint": "¶ 12",
    "sources": [
      {"name": "ndcourts", "url": "https://www.ndcourts.gov/supreme-court/opinion/2024ND156"},
      {"name": "courtlistener", "url": "https://www.courtlistener.com/c/ND/2024/156/"}
    ]
  }
]
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
  - (future) ndlegis.gov HTML — `https://www.ndlegis.gov/cencode/t{title}c{chapter}.html`

**N.D.A.C. (Admin Code)**
- **Canonical:** `N.D.A.C. § 43-02-05-01`
- **Forgiving:** `NDAC § 43-02-05-01`, `N.D. Admin. Code § 43-02-05-01`
- **Components:** 3-part chapter (title-article-chapter), optional 4th part (section)
- **Source:** ndlegis.gov — `https://ndlegis.gov/information/acdata/pdf/{p1}-{p2}-{p3}.pdf`

**ND Court Rules** (21 rule sets from cite2url)
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

Each medium-neutral pattern needs:
- A regex that matches the year + jurisdiction abbreviation + number pattern
- Handling of appellate court variants (e.g., `2011 IL App (1st) 101234`,
  `1999 UT App 16`, `2017 Ark. App. 605`)
- URL generation via the state's official court website (preferred) or
  CourtListener as fallback

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

**State-specific reporters** (selected high-volume):

| Reporter | Abbreviation(s) |
|----------|-----------------|
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
- All others → CourtListener: `https://www.courtlistener.com/c/{reporter}/{volume}/{page}/`

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

## Verification Mode

When `--verify` is passed:
1. For each generated URL, issue an HTTP HEAD request
2. Accept 200 or 3xx as verified
3. Mark as failed on 404, timeout, or connection error
4. Rate-limit requests (1 req/sec default, configurable)
5. Report verification results in output

Uses `httpx` for async HTTP. Verification is always optional — the tool works
fully offline for URL generation.

---

## URL Sources Reference

### Official Government Sources (preferred)

| Source | Base URL | Citation Types |
|--------|----------|---------------|
| govinfo.gov | `https://www.govinfo.gov/link/uscode/{title}/{section}` | U.S.C. |
| ecfr.gov | `https://www.ecfr.gov/current/title-{title}/section-{section}` | C.F.R. |
| constitutioncenter.org | `https://constitutioncenter.org/the-constitution/...` | U.S. Const. |
| ndcourts.gov | `https://www.ndcourts.gov/...` | ND opinions, ND rules |
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

Many state court websites do not support constructable URLs. In those cases,
CourtListener is the fallback for case citations and the state legislature
website (if available) for statutes.

---

## Implementation Plan

### Phase 1: Core Framework + ND (MVP)

1. **Project setup**
   - pyproject.toml with CLI entry point (`jetcite`)
   - Dependencies: `httpx` (verification), `click` (CLI)
   - Dev dependencies: `pytest`, `ruff`

2. **Data model** (models.py)
   - Citation, Source, CitationType dataclasses
   - Normalize helpers (Roman numeral conversion, period stripping)

3. **Pattern framework** (patterns/base.py)
   - Base matcher class with `match(text) -> list[Citation]` interface
   - Pattern registry with priority ordering
   - Forgiving regex builder helpers (optional periods, flexible whitespace)

4. **Federal patterns** — port from cite2url + jetredline
   - U.S. Constitution (constitutions.py)
   - U.S.C. and C.F.R. (federal_statutes.py)
   - Federal rules (federal_rules.py)
   - All federal case reporters (federal_cases.py)
   - All regional reporters (regional.py)
   - U.S. Reports via Justia (federal_cases.py)

5. **Medium-neutral citations** (neutral.py)
   - All 21 jurisdictions from the table above
   - Appellate court variants

6. **North Dakota module** (states/nd.py)
   - NDCC sections and chapters
   - NDAC sections and chapters
   - All 21 ND court rule sets
   - ND Constitution
   - URL generation for ndcourts.gov, ndlegis.gov, ndconst.org

7. **Resolver** (resolver.py)
   - Route citations to appropriate source modules
   - Generate URLs with pinpoint anchors where supported
   - Optional HTTP verification with rate limiting

8. **Scanner** (scanner.py)
   - Batch mode: scan document text, find all citations
   - Deduplication by normalized citation text
   - Position tracking for context

9. **CLI** (cli.py)
   - Single-citation and batch modes
   - Output formats: url, json, table
   - --verify, --open, --from-clipboard, --all-sources flags

10. **Tests** for all of the above

### Phase 2: Expand State Coverage

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

### Phase 3: Enhanced Features

- **Id. citation tracking** (see Future Enhancements below)
- **Parallel citation detection** — recognize when multiple citations refer to
  the same case (e.g., `2024 ND 156, 10 N.W.3d 500`)
- **Citation normalization** — convert informal citations to Bluebook form
- **Export formats** — Markdown with hyperlinks, HTML

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

This is a v2 feature. The data model already supports it — the scanner just
needs state tracking.

### Other Future Features

- **Supra/infra support** — resolve references to earlier/later citations in
  the same document
- **CourtListener API integration** — use the citation-lookup API for richer
  case metadata (case name, date, court)
- **Pattern export** — generate regex patterns in JSON/YAML for use by
  non-Python consumers (cite-linker-pro, cite2url)
- **Short-form citation resolution** — e.g., `Smith, 585 N.W.2d at 128`
  resolved against earlier full citation

---

## Dependencies

### Runtime
- `click` — CLI framework
- `httpx` — async HTTP for verification mode

### Development
- `pytest` — testing
- `ruff` — linting and formatting

### No dependency on
- Any PDF library (consuming projects handle their own document formats)
- Any AI/LLM library (pure regex parsing)
- Any database (stateless operation)

---

## Porting Notes

### From cite2url (Swift)

The most complete source for regex patterns and URL generation. Port:
- 21 ND court rule patterns (NDCourtRules.swift)
- NDCC section/chapter patterns (NDCC.swift)
- NDAC patterns (NDAC.swift)
- ND Constitution patterns (NDConstitution.swift)
- US Constitution patterns (USConstitution.swift)
- Federal statute patterns (FederalStatutes.swift)
- All state case patterns (StateCases.swift) — regional + neutral + state-specific
- All federal reporter patterns (FederalReporters.swift)
- URL generation logic (URLBuilder.swift) — 14 URL builder functions

### From jetredline (nd_cite_check.py)

Already Python. Reusable patterns and logic:
- Forgiving regex variants (flexible periods/spacing) already implemented
- Parallel citation detection in scan_opinion()
- Deduplication logic
- Citation record structure (similar to our Citation model)

### From jetmemo-skill (verify_citations.py)

- Multi-source verification chain pattern (local → web → API)
- CourtListener API interaction pattern (for future API integration)
- Rate limiting approach
