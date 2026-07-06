# Scope: Arizona and Iowa citation support

Scoping doc for adding deep(er) coverage of Arizona and Iowa primary law,
following the North Dakota model (a per-state `patterns/states/{xx}.py` matcher
plus per-source URL builders in `sources/`). Research below was empirically
verified by fetching candidate URLs and matching extracted text against the
citation, except where noted.

## Objective

jetcite's value proposition is a **deterministic URL to an official government
source, built purely from parsed citation components** (no network round-trip).
The central research question was: for each category of AZ/IA primary law, can we
build such a URL, or must we fall back to a search-then-resolve step or a
third-party aggregator (CourtListener / Justia)?

## What already works incidentally (no new code)

The generic `RegionalReporterMatcher` already links the reporters these states
actually publish in, routed to CourtListener:

- **Arizona opinions** → Pacific Reporter (`P.2d`/`P.3d`), `regional.py:31,38`.
- **Iowa opinions** → North Western Reporter (`N.W.2d`), `regional.py:25,35`.

Both are tagged `jurisdiction="us"` and point at CourtListener, not an official
state source. This is the *only* realistic target for opinions in either state
(see §Opinions), so opinions need no new deterministic builder — only, at most,
correct jurisdiction tagging and adding the official reporters `Ariz.` /
`Ariz. App.` to the matcher (Iowa has no live official reporter — *Iowa Reports*
ended in 1968 at vol. 261; modern Iowa cases appear only in N.W.2d).

## Buildability matrix (verified)

| Category | AZ official host | AZ buildability | IA official host | IA buildability |
|---|---|---|---|---|
| Statutes | azleg.gov | **DETERMINISTIC**, section-level | legis.iowa.gov | **DETERMINISTIC**, section-level |
| Admin code | apps.azsos.gov | DETERMINISTIC to **chapter PDF** only | legis.iowa.gov | **DETERMINISTIC**, rule-level |
| Court rules | azcourts.gov | **NOT BUILDABLE** (opaque viewer IDs) | legis.iowa.gov | DETERMINISTIC to **chapter PDF** only |
| Opinions | azcourts.gov | **NOT BUILDABLE** → CourtListener | iowacourts.gov | **NOT BUILDABLE** → CourtListener |
| Constitution | azleg.gov | **DETERMINISTIC**, section-level | legis.iowa.gov | **NOT BUILDABLE** to section (whole-doc PDF only) |

Neither state has adopted a public-domain / medium-neutral citation. There is no
"2024 AZ 12" or Iowa equivalent (confidence: high). **The existing `AZ` entry in
`neutral.py:41,178` is therefore spurious and should be removed** — it matches a
format that never appears in real Arizona text and is a false-positive magnet.

## Verified URL templates

### Arizona — DETERMINISTIC categories

**Statutes (A.R.S.)** — `sources/azleg.py`
```
https://www.azleg.gov/ars/{title}/{section}.htm
```
- `{title}`: not padded (`13`, `2`, `41`)
- `{section}`: **zero-padded to 5 digits**; a decimal `.NN` becomes `-NN`
  - `13-1105` → `/ars/13/01105.htm`  (verified: "First degree murder")
  - `13-105`  → `/ars/13/00105.htm`
  - `12-821.01` → `/ars/12/00821-01.htm`

**Constitution (Ariz. Const.)** — `sources/azleg.py`
```
https://www.azleg.gov/const/{article}/{section}.htm
```
- arabic article number; section not padded
  - `art. 2, § 4` → `/const/2/4.htm`  (verified: "Due process of law")
- **Article 4 exception:** it is split into Parts, sections take a `.p{part}`
  suffix — `/const/4/2.p2.htm` = art. 4, pt. 2, § 2. Special-case article 4.

**Admin code (A.A.C.)** — `sources/azsos.py` — chapter PDF only
```
https://apps.azsos.gov/public_services/Title_{title:02d}/{title}-{chapter:02d}.pdf
```
- folder `Title_{NN}` padded to 2; filename `{title}-{chapter:02d}` (title
  unpadded, chapter padded to 2)
  - `R20-6-201` → `/public_services/Title_20/20-06.pdf`
- The section (`-201`) is *inside* the PDF; **no section-level anchor**. The
  citation's section component is not used in the URL.
- Structure confirmed via search index + LII cross-reference; direct fetch is
  bot-blocked (403), so a runtime liveness check will fail on this host — treat
  403 from apps.azsos.gov as "assume live," not "dead."

### Iowa — DETERMINISTIC categories

**Statutes (Iowa Code)** — `sources/ialegis.py`
```
https://www.legis.iowa.gov/docs/code/{chapter}.{section}.pdf
```
- The section number *is* `{chapter}.{section}` — the file basename is literally
  the citation.
  - `707.2` → `/docs/code/707.2.pdf`  (verified: "Murder in the first degree")
  - chapter-only ("ch. 707") → `/docs/code/707.pdf`
- Serves the current edition; no year in the URL. (Historical editions use a
  different template: `/docs/iacode/{year}/{chapter}/{section}.html` — only
  needed if a citation carries an old code year.)
- A bogus section 404s, so 200 + `application/pdf` is a meaningful positive.

**Admin code (Iowa Admin. Code)** — `sources/ialegis.py` — rule-level
```
https://www.legis.iowa.gov/docs/aco/rule/{agency}.{rule}.pdf
```
- citation `657-8.1` (agency 657, ch. 8, rule .1): hyphen → dot
  - `657-8.1` → `/docs/aco/rule/657.8.1.pdf`  (verified: "657—8.1(155A) Purpose and scope")
- **Do NOT use** the chapter endpoint `/docs/aco/chapter/{agency}.{chapter}.pdf` —
  it returns 200 but serves the wrong (Chapter 1 / compiled) document. A
  status-only liveness check would wrongly "confirm" it. Rule-level only.

**Court rules (Iowa R. Civ./Crim./Evid./App. P.)** — `sources/ialegis.py` — chapter PDF
```
https://www.legis.iowa.gov/docs/ACO/CourtRulesChapter/{chapter}.pdf
```
- `{chapter}` = the integer before the dot in the rule number:
  - Civ. P. 1.302 → `1.pdf`; Crim. P. 2.x → `2.pdf`; Evid. 5.401 → `5.pdf`;
    App. P. 6.904 → `6.pdf`  (chapters 1 and 6 verified)
- Multi-MB whole-chapter PDFs, **no rule-level anchor** — lands the reader in the
  right document but not at the rule.

### Non-buildable categories → aggregator fallback

- **AZ court rules:** azcourts.gov serves whole-document PDFs through a
  DotNetNuke viewer with opaque `moduleid`/`attachmentid` DB keys — not
  citation-derivable. Fallback: Justia (`law.justia.com/codes/arizona/...`,
  per-rule paths) or link to the `azcourts.gov/rules/...` set landing page
  (document-level, not official-deep).
- **AZ & IA opinions:** official sites key opinions by court/year/docket (AZ:
  `.../OpinionFiles/{Supreme|Div1|Div2}/{year}/{[Party-]Docket}.pdf` with
  unpredictable party prefix + `?ver=` token; IA: opaque CMS collection IDs).
  Neither is derivable from a reporter cite. Fallback: CourtListener (already
  wired) → Google Scholar/Justia.
- **IA constitution:** only a whole-document codified PDF at an opaque
  publication ID (`/docs/publications/icnst/402726.pdf`); no per-section URL.
  Options: hard-code the whole-doc PDF link (official but not section-specific),
  or fall back to Justia (`law.justia.com/constitution/iowa/article-i/section-8/`,
  section-derivable, aggregator tier).

## Proposed implementation

New files, mirroring the ND layout:

- `src/jetcite/sources/azleg.py` — `ars_section_url()`, `az_constitution_url()`
- `src/jetcite/sources/azsos.py` — `aac_chapter_url()`
- `src/jetcite/sources/ialegis.py` — `iowa_code_url()`, `iowa_admin_rule_url()`,
  `iowa_court_rule_url()`
- `src/jetcite/patterns/states/az.py` — `AZMatcher` (statutes, constitution,
  admin code; register at priority 4-ish)
- `src/jetcite/patterns/states/ia.py` — `IAMatcher` (statutes, admin code, court
  rules)
- register both in `patterns/__init__.py:_auto_register()`
- tests: `tests/test_az.py`, `tests/test_ia.py` (mirror `test_nd.py`)

Regex work is the bulk of the effort. The A.R.S., Iowa Code, and admin-code
citation forms are simpler than NDCC/NDAC (fewer decimal-group permutations), so
each state matcher should be materially smaller than `nd.py` (654 lines).

Cleanup / correctness:
- Remove the `AZ` token from `_STANDARD_NEUTRAL` (`neutral.py:41`) and the
  `"AZ": "az"` map entry (`neutral.py:178`); drop `AZ` from the README's
  "21 jurisdictions" list (`README.md:313`).
- Add `Ariz.` and `Ariz. App.` to `_STATE_REPORTERS` (`regional.py:63-67`) and
  consider tagging Pacific-Reporter AZ / N.W.2d IA cites with the state
  jurisdiction where distinguishable (low value; optional).
- Extend `~/refs/` layout (`cache.py`) with `az/` and `ia/` subtrees if caching
  is desired.
- The apps.azsos.gov 403 bot-block means the optional HTTP liveness check
  (`--verify`) must not treat 403 as dead for that host.

## Effort estimate (rough)

Reference class: the ND module is one large file built incrementally. AZ and IA
are simpler (no multi-part decimal statute numbers like NDCC 12.1-32-01, fewer
rule sets to special-case).

- **Arizona:** statutes + constitution + admin-chapter builder + matcher + tests
  — ~0.5–1 day. The three buildable categories are clean.
- **Iowa:** statutes + admin-rule + court-rule-chapter builder + matcher + tests
  — ~0.5–1 day. Watch the admin chapter-endpoint false-positive.

Confidence: moderate. The regex/URL work is well-understood and mirrors ND; the
risk is edge cases in citation formatting (decimal sections, chapter-only cites,
prose forms like "Section X of the Arizona Revised Statutes").

## Implementation status (2026-07-05)

Implemented and tested (`patterns/states/az.py`, `patterns/states/ia.py`,
`sources/azleg.py`, `sources/azsos.py`, `sources/ialegis.py`; 500-test suite
green; end-to-end verified through `scan_text`):

- **AZ:** A.R.S. statutes, A.A.C. (chapter PDF), Ariz. Constitution (incl. art. 4
  Parts); `Ariz.`/`Ariz. App.` reporter added to `regional.py`; spurious `AZ`
  neutral entry removed.
- **IA:** Iowa Code (section + chapter), Iowa Admin. Code (rule PDF), Iowa Court
  Rules (chapter PDF), Iowa Constitution (whole-doc PDF).
- Opinions for both: unchanged — already routed to CourtListener via reporters.

**AZ court rules — recognized, linked to the official rules index.** The
originally-agreed Justia fallback does not exist (Justia hosts only the Arizona
Revised Statutes), and azcourts.gov serves rule text solely through an opaque
DotNetNuke viewer (`rulesforum.azcourts.gov/...viewer.aspx?...attachmentid=`)
with no citation-derivable path. Rather than a dead/guessed deep link, a
recognized rule cite (e.g. `Ariz. R. Civ. P. 12`) links to the official rules
index `https://www.azcourts.gov/rules` (`sources/azcourts.py`) — document-level,
not rule-precise. The family regex requires known rule-set tokens, so
`Ariz. Rev. Stat.` is never mis-read as a rule.

## Open decisions

1. **Court rules & non-section constitution:** accept aggregator/whole-doc
   fallbacks (Justia for AZ rules; whole-PDF or Justia for IA constitution), or
   leave those categories unsupported? Recommendation: link the official
   whole-document target where one exists (IA court-rule chapter PDF, IA
   constitution codified PDF) and use Justia only where there is no official
   deep-linkable document (AZ rules).
2. **Opinions:** rely entirely on the existing CourtListener path (recommended —
   there is no official alternative), and optionally add `Ariz.`/`Ariz. App.`
   reporter recognition.
3. **Value bar for chapter-level links** (AZ admin, IA court rules): landing the
   reader in the correct multi-page PDF without an in-document anchor — does that
   clear the bar, or only section/rule-level links count?
