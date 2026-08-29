#!/usr/bin/env python3
"""Find code blocks and tables that nobody introduced.

A heading followed immediately by a fenced command tells the reader what the step is
called but not what the command does, whether it is safe, or what they should see
afterwards. The heading is a label, not a sentence. Readers who arrive mid document, or
who are skimming for the one command they need, have to reconstruct the intent from the
command itself, which is exactly the work a runbook exists to save them.

So every fenced block and every table needs at least one line of prose immediately before
it. A preceding line counts as an introduction when it is ordinary text: a paragraph, a
list item, a bold `**Run from:**` annotation. It does not count when it is a heading, a
horizontal rule, the end of another fence, the last row of a table, or the top of the file.

Usage:
    python tools/check_intros.py github-ssh-setup.md
    python tools/check_intros.py *.md --quiet
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^\s*#{1,6}\s")
RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
TABLE_ROW = re.compile(r"^\s*\|")
COMMENT = re.compile(r"^\s*<!--")


def introduces(line: str) -> bool:
    """Is this line ordinary prose that can serve as an introduction?"""
    if not line.strip():
        return False
    for pattern in (HEADING, RULE, FENCE, TABLE_ROW, COMMENT):
        if pattern.match(line):
            return False
    return True


def previous_meaningful(lines, index: int):
    """Walk back past blank lines. Returns (line, line_number) or (None, None)."""
    i = index - 1
    while i >= 0 and not lines[i].strip():
        i -= 1
    if i < 0:
        return None, None
    return lines[i], i + 1


def find_orphans(text: str):
    """Return a list of (line_number, kind, preview, reason)."""
    lines = text.splitlines()
    orphans = []
    in_fence = False
    seen_table = set()

    for i, line in enumerate(lines):
        if FENCE.match(line):
            if in_fence:
                in_fence = False
                continue
            in_fence = True
            prev, prev_no = previous_meaningful(lines, i)
            if prev is None or not introduces(prev):
                reason = "start of file" if prev is None else describe(prev)
                orphans.append((i + 1, "code block", lines[i].strip() or "```", reason))
            continue

        if in_fence:
            continue

        # A table starts at its first row. Only report the first row of each table.
        if TABLE_ROW.match(line) and i not in seen_table:
            j = i
            while j < len(lines) and TABLE_ROW.match(lines[j]):
                seen_table.add(j)
                j += 1
            prev, prev_no = previous_meaningful(lines, i)
            if prev is None or not introduces(prev):
                reason = "start of file" if prev is None else describe(prev)
                orphans.append((i + 1, "table", line.strip()[:60], reason))

    return orphans


def describe(line: str) -> str:
    if HEADING.match(line):
        return "preceded by a heading: %s" % line.strip()[:60]
    if RULE.match(line):
        return "preceded by a horizontal rule"
    if FENCE.match(line):
        return "preceded by another fenced block"
    if TABLE_ROW.match(line):
        return "preceded by a table row"
    if COMMENT.match(line):
        return "preceded by an HTML comment"
    return "preceded by %s" % line.strip()[:60]


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check_intros.py",
        description="Find code blocks and tables with no introductory prose.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("inputs", nargs="+", help="Markdown files to check.")
    parser.add_argument("--quiet", action="store_true", help="Print only the counts.")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    total = 0

    for name in args.inputs:
        path = Path(name)
        if not path.is_file():
            print("skip   %s (not a file)" % path, file=sys.stderr)
            continue

        orphans = find_orphans(path.read_text(encoding="utf-8"))
        total += len(orphans)

        if not orphans:
            print("%s: every block and table is introduced" % path)
            continue

        print("%s: %d without an introduction" % (path, len(orphans)))
        if not args.quiet:
            for line_no, kind, preview, reason in orphans:
                print("  line %-5d %-11s %-22s %s" % (line_no, kind, preview, reason))

    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
