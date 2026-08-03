---
name: jetcite
version: 2.8.1
description: Parse American legal citations from text and generate URLs to official government sources.
---

# jetcite — Legal Citation Parser and Linker

Parse American legal citations from text and generate URLs to official government sources.

**Update check:** On first use in a session, run `python3 "${CLAUDE_SKILL_DIR}/check_update.py"` silently. If it prints output, include it as a note to the user.

`${CLAUDE_SKILL_DIR}` here and below is replaced by the harness with this skill's absolute directory (standalone install, plugin cache, or Cowork mount alike) before you read this file — the paths you see are literal. Keep them double-quoted in shell commands.

## Installation

Extract the `jetcite-skill` zip to `~/.claude/skills/jetcite-skill/`.

## Tools

### Look up a single citation

```bash
python "${CLAUDE_SKILL_DIR}/jetcite_tool.py" lookup "585 N.W.2d 123"
```

Returns the primary URL for the citation. Add `--json` for full structured output including citation type, jurisdiction, normalized form, and all available source URLs.

### Scan a document for all citations

```bash
python "${CLAUDE_SKILL_DIR}/jetcite_tool.py" scan /path/to/document.md
```

Returns all citations found with their URLs (tab-separated). Add `--json` for structured output.

To scan text from stdin:

```bash
echo "See 2024 ND 156 and N.D.C.C. § 1-02-13." | python "${CLAUDE_SKILL_DIR}/jetcite_tool.py" scan -
```

### Use as a Python library

```python
import sys
sys.path.insert(0, "${CLAUDE_SKILL_DIR}/src")  # rendered as this skill's absolute path
from jetcite import lookup, scan_text

cite = lookup("2024 ND 156")
citations = scan_text(document_text)
```

## Supported citations

- **Federal:** U.S. Constitution, U.S.C., C.F.R., federal rules (FRCP, FRE, FRAP, etc.), all federal case reporters
- **Regional reporters:** N.W.2d, A.3d, S.E.2d, So.3d, S.W.3d, N.E.3d, P.3d, plus state-specific reporters
- **Medium-neutral:** 21 jurisdictions (AR, CO, IL, MT, ND, OH, OK, SD, UT, WI, WY, etc.)
- **North Dakota (deep):** NDCC, NDAC, ND Constitution, 21 court rule sets, ND Reports

## Output format (JSON)

Each citation includes:

- `raw_text` — original matched text
- `cite_type` — case, statute, constitution, court_rule, regulation
- `jurisdiction` — "us", "nd", etc.
- `normalized` — canonical Bluebook form
- `sources` — list of `{name, url}` objects
- `parallel_cites` — related citations for the same case
