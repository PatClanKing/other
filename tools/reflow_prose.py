#!/usr/bin/env python3
"""Join hard wrapped prose so GitHub does not render the wrapping as line breaks.

GitHub Flavored Markdown treats a single newline inside a paragraph as a hard break and
emits `<br>`. That is convenient in a comment box and wrong in a document: prose wrapped
at some column in the editor renders with ragged breaks mid sentence, at whatever width
the author's editor happened to use rather than the reader's window.

    Everything here stays inside Git Bash. The commands are plain POSIX shell, so the same
    lines also
    work on macOS and Linux.

The fix is to write each paragraph as one long source line and let the renderer wrap it.
This script does that, joining continuation lines within paragraphs, list items and block
quotes, and leaving everything that depends on its own line alone:

  1. Fenced code blocks, including fences indented inside a list item.
  2. Tables, where each row must stay on its own line.
  3. Headings, horizontal rules and HTML comments such as the table of contents markers.
  4. Deliberate hard breaks, which in Markdown are two trailing spaces or a backslash.

Usage:
    python tools/reflow_prose.py github-ssh-setup.md --check
    python tools/reflow_prose.py github-ssh-setup.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FENCE = re.compile(r"^(\s*)(```|~~~)")
HEADING = re.compile(r"^\s*#{1,6}\s")
RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
TABLE_ROW = re.compile(r"^\s*\|")
COMMENT = re.compile(r"^\s*<!--")
LIST_ITEM = re.compile(r"^(\s*)((?:\d+\.|[*+-])\s+)(.*)$")
QUOTE = re.compile(r"^(\s*)>\s?(.*)$")
# Markdown's own hard break syntax. If the author asked for a break, keep it.
EXPLICIT_BREAK = re.compile(r"(  |\\)$")


def is_block_start(line: str) -> bool:
    """Lines that begin something which must not be joined onto a previous line."""
    return bool(
        HEADING.match(line)
        or RULE.match(line)
        or TABLE_ROW.match(line)
        or COMMENT.match(line)
        or FENCE.match(line)
        or LIST_ITEM.match(line)
        or QUOTE.match(line)
    )


def reflow(text: str):
    """Return (new_text, joins) where joins lists the line numbers that were merged."""
    lines = text.splitlines()
    out = []
    joins = []
    in_fence = False
    fence_marker = ""

    for number, line in enumerate(lines, start=1):
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(2)
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence = False
            out.append(line)
            continue

        if in_fence or not line.strip() or is_block_start(line):
            out.append(line)
            continue

        # A plain text line. Join it onto the previous one when that one is still an open
        # paragraph, list item or quote, rather than a structural line.
        previous = out[-1] if out else ""
        can_join = (
            bool(previous.strip())
            and not FENCE.match(previous)
            and not HEADING.match(previous)
            and not RULE.match(previous)
            and not TABLE_ROW.match(previous)
            and not COMMENT.match(previous)
            and not EXPLICIT_BREAK.search(previous)
        )
        # A quoted line continues a quote, not a bare paragraph.
        if can_join and QUOTE.match(previous):
            can_join = False

        if can_join:
            out[-1] = previous.rstrip() + " " + line.strip()
            joins.append(number)
        else:
            out.append(line)

    result = "\n".join(out)
    if text.endswith("\n"):
        result += "\n"
    return result, joins


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="reflow_prose.py",
        description="Join hard wrapped prose so GitHub does not render it as line breaks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("inputs", nargs="+", help="Markdown files to reflow.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report wrapped paragraphs without writing. Exits 1 if any are found.",
    )
    parser.add_argument("--quiet", action="store_true", help="Print counts only.")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    total = 0

    for name in args.inputs:
        path = Path(name)
        if not path.is_file():
            print("skip   %s (not a file)" % path, file=sys.stderr)
            continue

        text = path.read_text(encoding="utf-8")
        updated, joins = reflow(text)
        total += len(joins)

        if not joins:
            print("%s: no wrapped prose, renders without stray breaks" % path)
            continue

        verb = "would join" if args.check else "joined"
        print("%s: %s %d wrapped line(s)" % (path, verb, len(joins)))
        if not args.quiet:
            preview = ", ".join(str(n) for n in joins[:20])
            more = "" if len(joins) <= 20 else ", and %d more" % (len(joins) - 20)
            print("  source lines: %s%s" % (preview, more))

        if not args.check:
            path.write_text(updated, encoding="utf-8")
            print("  wrote %s" % path)

    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    raise SystemExit(main())
