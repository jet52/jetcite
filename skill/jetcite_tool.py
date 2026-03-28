#!/usr/bin/env python3
"""Standalone jetcite wrapper — no external dependencies required.

Usage:
    python jetcite_tool.py lookup "585 N.W.2d 123"
    python jetcite_tool.py scan document.md
    python jetcite_tool.py scan -              # read from stdin
"""

import argparse
import json
import sys
from pathlib import Path

# Add the bundled src/ directory to the import path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from jetcite import lookup, scan_text  # noqa: E402


def cmd_lookup(args):
    text = args.citation
    if text == "-":
        text = sys.stdin.read().strip()
    cite = lookup(text)
    if cite is None:
        print(f"No citation pattern matched: {text}", file=sys.stderr)
        sys.exit(1)
    if args.json:
        print(json.dumps(cite.to_dict(), indent=2))
    else:
        if cite.sources:
            print(cite.sources[0].url)
        else:
            print(cite.normalized)


def cmd_scan(args):
    if args.file == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.file).read_text()
    citations = scan_text(text)
    if args.json:
        print(json.dumps([c.to_dict() for c in citations], indent=2))
    else:
        for cite in citations:
            url = cite.sources[0].url if cite.sources else "(no URL)"
            print(f"{cite.normalized}\t{url}")


def main():
    from check_update import check_for_update
    update_msg = check_for_update()
    if update_msg:
        print(f"Note: {update_msg}", file=sys.stderr)

    parser = argparse.ArgumentParser(
        description="jetcite — American legal citation parser and linker"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_lookup = sub.add_parser("lookup", help="Look up a single citation")
    p_lookup.add_argument("citation", help="Citation text (or '-' for stdin)")
    p_lookup.add_argument("--json", action="store_true", help="Output as JSON")
    p_lookup.set_defaults(func=cmd_lookup)

    p_scan = sub.add_parser("scan", help="Scan a document for all citations")
    p_scan.add_argument("file", help="File path to scan (or '-' for stdin)")
    p_scan.add_argument("--json", action="store_true", help="Output as JSON")
    p_scan.set_defaults(func=cmd_scan)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
