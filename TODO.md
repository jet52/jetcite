# Plan: Cache Web-Retrieved Citations in ~/refs

## Problem

`verify_citations.py` resolves citation URLs but never fetches or stores content. Every pipeline run re-resolves the same URLs against CourtListener, Justia, and ndcourts.gov. For permanent content like court opinions, this is unnecessary network load on free public services and slows down subsequent runs.

The `jetcite` library already has a `fetch_and_cache()` function in `cache.py` with source-specific extractors for CourtListener and Justia, a well-defined `~/refs/` directory layout, `.meta.json` sidecar files with fetch timestamps, and staleness thresholds per citation type. None of this is wired into the scanning pipeline.

## Design Principles

1. **Permanent content gets cached permanently.** Court opinions are fixed historical artifacts. Once fetched, they never need re-fetching.
2. **Mutable content gets cached with staleness tracking.** Statutes, regulations, and court rules change through legislative sessions and rule amendments. Cache them, but mark them stale after a threshold period.
3. **The scanning step does the caching.** `verify_citations.py` runs early in the pipeline (Phase 1, Step 1). Caching here means Agent D (precedent lookup) and Agent E (statutory verification) read local files instead of making redundant network calls.
4. **Opt-in via flag.** Add `--cache` to `verify_citations.py`. Without the flag, behavior is unchanged (scan and resolve only). With the flag, web-only citations are fetched and stored.
5. **Respect `~/refs/` as read-only for pre-populated content.** The existing `nd/code/`, `nd/regs/`, `nd/rule/`, and `nd/opin/markdown/` directories may be maintained by a separate sync process. `fetch_and_cache` already checks for existing files before fetching, so it won't overwrite manually curated content.

## Staleness Policy

These thresholds are already defined in `cache.py` (`STALENESS_DAYS`):

| Citation Type           | Threshold        | Rationale                                                 |
| ----------------------- | ---------------- | --------------------------------------------------------- |
| Cases                   | None (permanent) | Published opinions don't change                           |
| Constitutions           | None (permanent) | Amendments are new provisions, not edits to existing ones |
| Statutes (NDCC, USC)    | 90 days          | Legislative sessions can amend; re-check quarterly        |
| Regulations (NDAC, CFR) | 90 days          | Agency rulemaking can amend                               |
| Court Rules             | 180 days         | Rules change less frequently; semi-annual check           |

## Cache Directory Layout

Already defined in `cache.py` `_citation_path()`:

```
~/refs/
├── nd/
│   ├── opin/
│   │   ├── markdown/      # ND neutral cites: {year}/{year}ND{number}.md
│   │   └── NW2d/          # ND historical reporters: {volume}/{page}.md
│   ├── code/              # NDCC; pre-populated, fetch_and_cache won't overwrite
│   ├── regs/              # NDAC; pre-populated, fetch_and_cache won't overwrite
│   ├── cnst/              # ND Constitution: art-{nn}/sec-{n}.md
│   └── rule/              # ND Court Rules; pre-populated, fetch_and_cache won't overwrite
├── us/
│   ├── scotus/            # U.S. Reports: {volume}/{page}.md
│   ├── F3d/               # Federal Reporter: {volume}/{page}.md
│   ├── usc/               # USC statutes: {title}/{section}.md
│   └── cfr/               # CFR regulations: {title}/{section}.md
└── reporter/
    └── NW2d/              # Non-ND state reporters: {volume}/{page}.md
```

Each cached file gets a `.meta.json` sidecar:

```json
{
  "citation": "571 N.W.2d 351",
  "source_url": "https://www.courtlistener.com/...",
  "fetched": "2026-03-27T19:45:00+00:00",
  "content_type": "text/markdown"
}
```

## Implementation

### Step 1: Add `--cache` flag to `verify_citations.py`

In the CLI `main()` function, add:

```python
parser.add_argument("--cache", action="store_true", default=False,
                    help="Fetch and cache web-only citations to ~/refs")
```

After `scan_citations()` returns the entries list, if `--cache` is set, iterate over the underlying `Citation` objects and call `fetch_and_cache` for any that lack a local file:

```python
if args.cache:
    from jetcite.cache import fetch_and_cache, resolve_local, is_stale
    refs_path = Path(args.refs_dir).expanduser()
    cached_count = 0
    stale_count = 0
    for cite in citations:
        local = resolve_local(cite, refs_path)
        if local is not None:
            # Check staleness for mutable types
            if is_stale(cite, local):
                stale_count += 1
                fetch_and_cache(cite, refs_path)
                cached_count += 1
        else:
            # No local file — fetch if we have a URL
            if any(s.name != "local" for s in cite.sources):
                result = fetch_and_cache(cite, refs_path)
                if result:
                    cached_count += 1
    print(f"Cached: {cached_count} | Stale refreshed: {stale_count}",
          file=sys.stderr)
```

This requires `scan_citations` to also return the raw `Citation` objects, not just the legacy dicts. See Step 2.

### Step 2: Expose raw Citation objects from `scan_citations`

Currently `scan_citations()` calls `scan_text()` (which returns `list[Citation]`) and then converts to legacy dicts via `_to_legacy()`. The raw `Citation` objects are discarded.

Options (pick one):

- **Option A:** Return both: `scan_citations()` returns `(entries, citations)` tuple. Requires updating all callers.
- **Option B (preferred):** Add `scan_citations_raw()` that returns `list[Citation]`. Keep `scan_citations()` unchanged for backward compatibility. The `--cache` codepath calls `scan_citations_raw()` instead.
- **Option C:** Store the `Citation` objects on the legacy dict entries (e.g., `entry["_citation_obj"] = cite`). Slightly hacky but zero API change.

Recommend **Option B** for cleanliness.

### Step 3: Handle `is_stale` for re-fetching mutable content

`is_stale()` already exists and reads the `.meta.json` sidecar. Currently it returns `True/False/None` but nothing acts on the return value. The `--cache` codepath (Step 1) will call `is_stale()` for citations that already have local files and re-fetch if stale.

One addition needed: `fetch_and_cache()` currently skips if a local file exists (line 280: `if existing is not None: return existing`). For stale re-fetching, add a `force=False` parameter:

```python
def fetch_and_cache(citation, refs_dir=None, timeout=10.0, force=False):
    ...
    existing = resolve_local(citation, refs_dir)
    if existing is not None and not force:
        add_local_source(citation, existing)
        return existing
    ...
```

The stale-refresh codepath passes `force=True`.

### Step 4: Update the jetmemo skill pipeline

In `SKILL.md`, Phase 1 Step 1, change the citation extraction command from:

```bash
cat *.txt | python3 ~/.claude/skills/jetmemo/scripts/verify_citations.py \
  --refs-dir ~/refs --json > citations.json
```

to:

```bash
cat *.txt | python3 ~/.claude/skills/jetmemo/scripts/verify_citations.py \
  --refs-dir ~/refs --json --cache > citations.json
```

No other pipeline changes needed. Agent D and Agent E already prefer local files when `local_exists` is `true` in `citations.json`. After caching, those fields will reflect the newly cached files.

### Step 5: Rate limiting and error handling

CourtListener and Justia are free public services. Add basic politeness:

- **Rate limit:** Add a small delay (0.5s) between fetches in the `--cache` loop. Not needed for the `resolve_local` check (no network), only for `fetch_and_cache` calls that actually hit the network.
- **Timeout:** `fetch_and_cache` already accepts a `timeout` parameter (default 10s). Keep it.
- **Failure tolerance:** If a fetch fails (network error, 404, rate limit), log a warning to stderr and continue. Don't fail the entire scan. The citation remains web-only in the output, same as today.
- **User-Agent header:** Set a descriptive User-Agent string (e.g., `jetcite/1.0 (legal-research-tool)`) so the services can identify the traffic. Add this to the httpx calls in `fetch_and_cache` and the source-specific extractors.

### Step 6: Tests

- Unit test: `fetch_and_cache` with a mocked httpx response writes the correct file to the correct path with a valid `.meta.json` sidecar.
- Unit test: `fetch_and_cache` with `force=False` skips when a local file exists; with `force=True` overwrites.
- Unit test: `is_stale` returns `True` for a statute cached 91 days ago, `False` for 89 days ago, `False` for a case regardless of age.
- Integration test: `verify_citations.py --cache` on a brief excerpt creates local files for web-only citations.
- Integration test: Second run of `verify_citations.py --cache` on the same input makes zero network calls (all local).

## Impact

For the Jones memo (20250429), this would have cached 11 state reporter opinions on the first run. On a second run, `verify_citations.py` would find all 78 citations locally (35 pre-existing + 11 newly cached + 25 ND neutral cites already local + 7 NDCC/rules already local) and make zero network calls. Agent D would read CourtListener markdown from `~/refs/reporter/` instead of fetching at runtime.

## Open Questions

1. **Should `link_citations.py` also benefit?** It reads `citations.json` and uses URLs for hyperlinking. If a citation is now cached locally, should the hyperlink point to the web URL (better for readers) or a local path? Probably keep web URLs for hyperlinks — caching is about reducing fetch burden, not changing the output format.

2. **Should the ND neutral cite fetcher cache to `nd/opin/markdown/`?** Currently `resolve_nd_opinion_url()` in `sources/ndcourts.py` hits ndcourts.gov to resolve redirect URLs during _scanning_ (not just caching). If we cache the opinion content, we could also cache the resolved URL to avoid the redirect-resolution network call. This would require a URL-only cache (no content) for the scanning step.

3. **CourtListener API vs. scraping?** The current CourtListener extractor appears to scrape opinion pages. CourtListener offers a free API (`/api/rest/v4/`) that returns structured JSON. Using the API would be more polite and reliable. Worth considering for a future iteration, but the current approach works and the volume is low.
