#!/usr/bin/env python3
"""Generate or refresh a table of contents in a Markdown file.

GitHub renders a document's outline behind the hamburger icon at the top right, but that
is hidden behind a click, and nothing but github.com reproduces it. A
literal list of anchor links at the top of the file works everywhere, which is why this
script exists.

The table of contents is written between two HTML comment markers, so re-running the
script replaces it rather than stacking copies:

    <!-- toc -->
    ... generated, do not edit by hand ...
    <!-- /toc -->

If the markers are absent, they are inserted after the document's opening block (the
first `---` horizontal rule following the title), which is where a reader expects them.

Usage:
    python tools/update_toc.py github-ssh-setup.md
    python tools/update_toc.py github-ssh-setup.md --depth 2
    python tools/update_toc.py *.md --check
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

START = "<!-- toc -->"
END = "<!-- /toc -->"

HEADING = re.compile(r"^(#{2,6})\s+(.*?)\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def strip_markdown(text: str) -> str:
    """Reduce heading markup to the plain text GitHub slugs from."""
    text = re.sub(r"`([^`]*)`", r"\1", text)          # inline code
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)    # bold
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)  # italic
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)     # links
    return text.strip()


def link_text(text: str) -> str:
    """Heading text as it should appear inside a contents entry.

    Only links are removed, because a link nested inside link text does not render.
    Everything else is kept deliberately. A heading such as "3.4 Get the `ssh-agent`
    running" must keep its backticks here: stripping them puts a bare hyphenated name
    back into prose, which is the exact thing the code span was there to prevent, and
    it would reintroduce a stray dash into a file whose whole point is not to have one.
    GitHub's slug ignores the backticks either way, so the anchor is unaffected.
    """
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).strip()


def github_slug(text: str, seen: dict) -> str:
    """Reproduce GitHub's heading anchor: lowercase, drop punctuation, spaces to hyphens.

    GitHub disambiguates repeats by appending -1, -2 and so on, so the same bookkeeping
    happens here. Without it, two headings with the same words would both link to the
    first one.
    """
    slug = strip_markdown(text).lower()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = slug.replace(" ", "-")

    if slug in seen:
        seen[slug] += 1
        return "%s-%d" % (slug, seen[slug])
    seen[slug] = 0
    return slug


def strip_toc(text: str) -> str:
    """Remove an existing table of contents block.

    This has to happen before headings are collected, otherwise the generated "Contents"
    heading is itself picked up as an entry and the file grows one bogus line on every
    run. In other words, the script would not be idempotent.
    """
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    return pattern.sub("", text)


def collect_headings(text: str, max_depth: int):
    """Return (level, title, slug) for every heading, ignoring anything inside a fence.

    Fenced blocks matter here: this repository's documents quote example headings inside
    code fences, and picking those up would produce entries pointing at nothing.
    """
    headings = []
    seen: dict = {}
    in_fence = False

    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2)
        slug = github_slug(title, seen)      # slug every heading, so numbering matches
        if level <= max_depth:
            headings.append((level, link_text(title), slug))
    return headings


def render_toc(headings) -> str:
    """Render the contents as an unordered list.

    Two deliberate choices here. The marker is `*` rather than an ordered `1.` because
    every heading already begins with its own section number, and an ordered list would
    render "1. 1. Git Bash specifics". It is `*` rather than the other unordered marker
    so the file contains no stray dash.
    """
    if not headings:
        return ""
    top = min(level for level, _, _ in headings)
    lines = ["## Contents", ""]
    for level, title, slug in headings:
        indent = "  " * (level - top)
        lines.append("%s* [%s](#%s)" % (indent, title, slug))
    return "\n".join(lines)


def apply_toc(text: str, toc: str) -> str:
    block = "%s\n\n%s\n\n%s" % (START, toc, END)

    if START in text and END in text:
        pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
        return pattern.sub(lambda _: block, text, count=1)

    # No markers yet. The table of contents belongs after the introduction and before the
    # first section, so anchor on the first level two heading. Anchoring on the first
    # horizontal rule instead looks equivalent but is not: a document whose intro has no
    # rule silently gets its contents dropped in after section 1.
    first_section = re.search(r"^## ", text, flags=re.M)
    if first_section:
        cut = first_section.start()
        head = text[:cut].rstrip()
        # Keep the document's section separator convention intact on both sides.
        if not head.endswith("---"):
            head += "\n\n---"
        return "%s\n\n%s\n\n---\n\n%s" % (head, block, text[cut:])

    # No sections at all, so put it directly under the title.
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("# "):
            head = "".join(lines[: i + 1])
            tail = "".join(lines[i + 1 :])
            return head + "\n" + block + "\n" + tail
    return block + "\n\n" + text


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="update_toc.py",
        description="Generate or refresh a Markdown table of contents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("inputs", nargs="+", help="Markdown files to update.")
    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Deepest heading level to list. 2 is sections only, 3 adds steps (default: 3).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report whether the table of contents is stale without writing. Exits 1 if so.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    stale = 0

    for name in args.inputs:
        path = Path(name)
        if not path.is_file():
            print("skip   %s (not a file)" % path, file=sys.stderr)
            stale += 1
            continue

        text = path.read_text(encoding="utf-8")
        headings = collect_headings(strip_toc(text), args.depth)
        updated = apply_toc(text, render_toc(headings))

        if updated == text:
            print("ok     %s (%d entries, already current)" % (path, len(headings)))
            continue

        if args.check:
            print("STALE  %s (%d entries would change)" % (path, len(headings)))
            stale += 1
            continue

        path.write_text(updated, encoding="utf-8")
        print("wrote  %s (%d entries, depth %d)" % (path, len(headings), args.depth))

    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
