#!/usr/bin/env python3
"""Find and replace identifying information in Markdown before it is published.

A runbook is written on one machine and read on many. Personal details leak in through
example commands almost by accident: the address you passed to `ssh-keygen -C`, the home
directory in a pasted `pwd`, the machine name in a prompt. None of it helps the reader,
and once it is pushed to a public repository it stays in the Git history.

Two categories, because they need different handling:

  REPLACE  Unambiguously personal and mechanically substitutable. Email addresses, the
           username inside a home directory path, machine hostnames. These are rewritten
           to angle bracket placeholders such as <email> and <username>.

  REVIEW   Needs a human decision, so it is reported and never touched. Key fingerprints,
           public key blobs, tokens and IP addresses. Some are secrets, some are load
           bearing: this repository's guide quotes GitHub's own published host key
           fingerprints, and scrubbing those would break the verification step.

Anything belonging to a service rather than a person is left alone, which is why
`git@github.com` survives while `you@example.org` does not.

Usage:
    python tools/scrub_pii.py github-ssh-setup.md --check
    python tools/scrub_pii.py github-ssh-setup.md
    python tools/scrub_pii.py *.md --extra "AcmeCorp=<company>"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Addresses that identify a service, not a person. These must survive untouched or the
# documented commands stop working.
SERVICE_ADDRESSES = {
    "git@github.com",
    "git@ssh.github.com",
    "git@gitlab.com",
    "git@bitbucket.org",
    "hg@bitbucket.org",
}

# (label, pattern, replacement)
REPLACE_RULES = [
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "<email>",
    ),
    (
        "windows home",
        re.compile(r"(?i)(C:\\Users\\)(?!<)([A-Za-z0-9._-]+)"),
        r"\1<username>",
    ),
    (
        "msys home",
        re.compile(r"(/c/Users/)(?!<)([A-Za-z0-9._-]+)"),
        r"\1<username>",
    ),
    (
        "unix home",
        re.compile(r"(/(?:home|Users)/)(?!<)([a-z][a-z0-9._-]*)"),
        r"\1<username>",
    ),
    (
        "hostname",
        re.compile(r"\b(?:LAPTOP|DESKTOP|MACBOOK|WIN)-[A-Z0-9]{5,}\b"),
        "<hostname>",
    ),
]

# (label, pattern, why it needs a human)
REVIEW_RULES = [
    ("ssh public key", re.compile(r"\bssh-(?:rsa|ed25519|dss)\s+AAAA[A-Za-z0-9+/=]{20,}")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("key fingerprint", re.compile(r"\bSHA256:[A-Za-z0-9+/=]{40,}")),
    ("github token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}")),
    ("generic secret", re.compile(r"(?i)\b(?:api[_-]?key|secret|password|passwd)\s*[=:]\s*\S{8,}")),
    ("ip address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]


def is_service_address(match_text: str) -> bool:
    return match_text.lower() in SERVICE_ADDRESSES


def scan_and_fix(text: str, extra: list):
    """Return (new_text, replacements, review_hits). Line numbers are of the original."""
    line_starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(i + 1)

    def line_of(pos: int) -> int:
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    replacements = []
    for label, pattern, repl in REPLACE_RULES + extra:
        def substitute(m: "re.Match", _label=label, _repl=repl):
            found = m.group(0)
            if _label == "email" and is_service_address(found):
                return found
            new = m.expand(_repl) if "\\" in _repl else _repl
            if new != found:
                replacements.append((line_of(m.start()), _label, found, new))
            return new

        text = pattern.sub(substitute, text)

    review = []
    for label, pattern in REVIEW_RULES:
        for m in pattern.finditer(text):
            review.append((line_of(m.start()), label, m.group(0)))

    return text, replacements, review


def parse_extra(values):
    """Turn `--extra "AcmeCorp=<company>"` into a replace rule."""
    rules = []
    for raw in values or []:
        if "=" not in raw:
            sys.exit("--extra needs the form FIND=REPLACE, got %r" % raw)
        find, repl = raw.split("=", 1)
        rules.append(("custom", re.compile(re.escape(find)), repl))
    return rules


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scrub_pii.py",
        description="Find and replace identifying information in Markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("inputs", nargs="+", help="Files to scan.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report findings without writing. Exits 1 if anything would be replaced.",
    )
    parser.add_argument(
        "--extra",
        action="append",
        metavar="FIND=REPLACE",
        help="Additional literal substitution, for example a username or company name.",
    )
    parser.add_argument(
        "--quiet-review",
        action="store_true",
        help="Do not print the review category. Findings there are never auto changed.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    extra = parse_extra(args.extra)
    total_replaced = 0

    for name in args.inputs:
        path = Path(name)
        if not path.is_file():
            print("skip   %s (not a file)" % path, file=sys.stderr)
            continue

        original = path.read_text(encoding="utf-8")
        updated, replacements, review = scan_and_fix(original, extra)

        print("%s" % path)
        if replacements:
            total_replaced += len(replacements)
            for line, label, found, new in replacements:
                verb = "would replace" if args.check else "replaced"
                print("  %-14s line %-4d %s  %s -> %s" % (label, line, verb, found, new))
        else:
            print("  clean, nothing to replace")

        if review and not args.quiet_review:
            print("  review by hand (never changed automatically):")
            seen = set()
            for line, label, found in review:
                snippet = found if len(found) <= 60 else found[:57] + "..."
                key = (label, snippet)
                if key in seen:
                    continue
                seen.add(key)
                print("    %-18s line %-4d %s" % (label, line, snippet))

        if replacements and not args.check:
            path.write_text(updated, encoding="utf-8")
            print("  wrote %s" % path)
        print()

    if args.check and total_replaced:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
