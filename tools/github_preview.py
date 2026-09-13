#!/usr/bin/env python3
"""Preview Markdown exactly as GitHub will render it, without uploading anything.

Two rendering modes:

  api      (default) Posts the Markdown to https://api.github.com/markdown with
           mode "gfm". This is GitHub's own renderer, so the HTML is identical to
           what github.com produces: task list checkboxes, autolinks, tables,
           strikethrough, footnotes and hard line breaks all behave the same.
           The document is sent to GitHub for rendering. It is not stored or
           published, but if that matters to you, use --offline instead.
           Unauthenticated calls are limited to 60 per hour. Set a GITHUB_TOKEN
           environment variable to raise that to 5000.

  offline  Renders locally with python-markdown. Close but not exact. No network
           traffic. Used automatically if the API call fails.

The result is wrapped in GitHub's own stylesheet (tools/assets/github-markdown.css),
which is vendored locally, so previewing works offline once generated.

Usage:
    python tools/github_preview.py github-ssh-setup.md
    python tools/github_preview.py github-ssh-setup.md --offline
    python tools/github_preview.py *.md --no-open
"""

from __future__ import annotations

import argparse
import html as html_module
import json
import os
import re
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
GITHUB_CSS = HERE / "assets" / "github-markdown.css"
DEFAULT_OUT_DIR = HERE / "out"

API_URL = "https://api.github.com/markdown"

# GitHub renders the article in a centred column with a light border.
PAGE_CSS = """
body {
    margin: 0;
    padding: 32px 16px;
    background-color: #ffffff;
    box-sizing: border-box;
}
.markdown-body {
    box-sizing: border-box;
    min-width: 200px;
    max-width: 1012px;
    margin: 0 auto;
    padding: 45px;
    border: 1px solid #d1d9e0;
    border-radius: 6px;
}
@media (prefers-color-scheme: dark) {
    body { background-color: #0d1117; }
    .markdown-body { border-color: #3d444d; }
}
@media (max-width: 767px) {
    .markdown-body { padding: 15px; }
}

/* Copy button. github.com adds this from its own web app, so the Markdown API
   never returns it. Recreated here to match the real reading experience. */
.code-wrap { position: relative; }
.code-wrap .copy-btn {
    position: absolute;
    top: 6px;
    right: 6px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    padding: 0;
    border: 1px solid #d1d9e0;
    border-radius: 6px;
    background-color: #f6f8fa;
    color: #59636e;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.1s ease-in-out;
}
.code-wrap:hover .copy-btn,
.code-wrap .copy-btn:focus { opacity: 1; }
.code-wrap .copy-btn:hover { background-color: #eaeef2; color: #1f2328; }
.code-wrap .copy-btn.copied { color: #1a7f37; border-color: #1a7f37; }
.code-wrap .copy-btn svg { width: 16px; height: 16px; fill: currentColor; }
@media (prefers-color-scheme: dark) {
    .code-wrap .copy-btn {
        border-color: #3d444d;
        background-color: #151b23;
        color: #9198a1;
    }
    .code-wrap .copy-btn:hover { background-color: #262c36; color: #f0f6fc; }
    .code-wrap .copy-btn.copied { color: #3fb950; border-color: #3fb950; }
}
"""

COPY_SCRIPT = """
<script>
(function () {
    var COPY_ICON = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"></path><path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"></path></svg>';
    var DONE_ICON = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 0 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path></svg>';

    // The textarea route works when the async clipboard API is unavailable or
    // refuses, which happens on insecure origins and when the document does not
    // hold focus.
    function legacyCopy(text) {
        return new Promise(function (resolve, reject) {
            var area = document.createElement('textarea');
            area.value = text;
            area.style.position = 'fixed';
            area.style.top = '0';
            area.style.opacity = '0';
            document.body.appendChild(area);
            area.focus();
            area.select();
            var ok = false;
            try {
                ok = document.execCommand('copy');
            } catch (err) {
                ok = false;
            }
            document.body.removeChild(area);
            ok ? resolve() : reject(new Error('execCommand copy failed'));
        });
    }

    function copyText(text) {
        if (navigator.clipboard && window.isSecureContext) {
            return navigator.clipboard.writeText(text).catch(function () {
                return legacyCopy(text);
            });
        }
        return legacyCopy(text);
    }

    document.querySelectorAll('.markdown-body pre').forEach(function (pre) {
        // The API wraps fenced code in div.highlight; plain <pre> needs its own wrapper.
        var host = pre.parentElement;
        if (!host.classList.contains('highlight')) {
            host = document.createElement('div');
            pre.parentNode.insertBefore(host, pre);
            host.appendChild(pre);
        }
        host.classList.add('code-wrap');

        var button = document.createElement('button');
        button.className = 'copy-btn';
        button.type = 'button';
        button.title = 'Copy';
        button.setAttribute('aria-label', 'Copy code to clipboard');
        button.innerHTML = COPY_ICON;

        button.addEventListener('click', function () {
            copyText(pre.innerText).then(function () {
                button.innerHTML = DONE_ICON;
                button.classList.add('copied');
                button.title = 'Copied';
                setTimeout(function () {
                    button.innerHTML = COPY_ICON;
                    button.classList.remove('copied');
                    button.title = 'Copy';
                }, 1600);
            }).catch(function () {
                button.title = 'Copy failed, select the text manually';
            });
        });

        host.appendChild(button);
    });
})();
</script>
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<style>
{github_css}
{page_css}
</style>
</head>
<body>
<article class="markdown-body">
{body}
</article>
{copy_script}
</body>
</html>
"""


def render_via_api(markdown_text: str, context: str | None) -> str:
    """Ask GitHub to render the Markdown. Returns the HTML fragment."""
    payload = {"text": markdown_text, "mode": "gfm"}
    if context:
        payload["context"] = context

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
        "User-Agent": "md-github-preview",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token

    request = urllib.request.Request(
        API_URL, data=json.dumps(payload).encode("utf-8"), headers=headers
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining is not None and remaining.isdigit() and int(remaining) < 10:
            print(
                "       note: %s GitHub API calls left this hour. Set GITHUB_TOKEN "
                "to raise the limit, or use --offline." % remaining,
                file=sys.stderr,
            )
        return response.read().decode("utf-8")


def add_heading_anchors(html: str) -> str:
    """Give every heading the id github.com would give it.

    The Markdown API returns bare `<h2>` tags with no id, because github.com adds the
    anchors itself when it renders the page. Without them a table of contents built from
    `#slug` links looks fine but goes nowhere in the preview, which defeats the point of
    previewing. The slug rule matches GitHub's: lowercase, drop punctuation, spaces to
    hyphens, and disambiguate repeats with a numeric suffix.
    """
    seen: dict = {}

    def slugify(inner: str) -> str:
        text = re.sub(r"<[^>]+>", "", inner)
        text = html_module.unescape(text).strip().lower()
        text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
        text = text.replace(" ", "-")
        if text in seen:
            seen[text] += 1
            return "%s-%d" % (text, seen[text])
        seen[text] = 0
        return text

    def replace(match: "re.Match") -> str:
        level, attrs, inner = match.group(1), match.group(2), match.group(3)
        if "id=" in attrs:
            return match.group(0)
        return '<h%s%s id="%s">%s</h%s>' % (level, attrs, slugify(inner), inner, level)

    return re.sub(r"<h([1-6])([^>]*)>(.*?)</h\1>", replace, html, flags=re.S)


def render_offline(markdown_text: str) -> str:
    """Local approximation. Close to GitHub Flavored Markdown but not identical."""
    try:
        import markdown
    except ImportError:
        sys.exit(
            "Offline rendering needs the 'markdown' package. Run the setup script "
            "or: pip install -r tools/requirements.txt"
        )

    converter = markdown.Markdown(
        extensions=["extra", "sane_lists", "nl2br", "admonition"],
    )
    return converter.convert(markdown_text)


def build_page(md_path: Path, args: argparse.Namespace) -> tuple[str, str]:
    text = md_path.read_text(encoding="utf-8")

    mode = "offline" if args.offline else "api"
    if mode == "api":
        try:
            body = render_via_api(text, args.context)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            print(
                "       GitHub API unavailable (%s). Falling back to offline rendering."
                % exc,
                file=sys.stderr,
            )
            body = render_offline(text)
            mode = "offline (fallback)"
    else:
        body = render_offline(text)

    body = add_heading_anchors(body)

    if not GITHUB_CSS.exists():
        sys.exit(
            "Missing %s. Re-download it with:\n"
            "  curl -sL https://cdn.jsdelivr.net/npm/github-markdown-css@5/github-markdown.css "
            "-o tools/assets/github-markdown.css" % GITHUB_CSS
        )

    html = HTML_TEMPLATE.format(
        title=md_path.name,
        github_css=GITHUB_CSS.read_text(encoding="utf-8"),
        page_css=PAGE_CSS,
        body=body,
        copy_script=COPY_SCRIPT,
    )
    return html, mode


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="github_preview.py",
        description="Preview Markdown as GitHub renders it.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Markdown files. Defaults to every .md file in the repository root.",
    )
    parser.add_argument(
        "-o", "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="Where the HTML preview is written (default: tools/out).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Render locally instead of calling GitHub. No network traffic, slightly less exact.",
    )
    parser.add_argument(
        "--context",
        help="Repository for resolving #123 and @user links, in the form <owner>/<repo>.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the preview in a browser.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.inputs:
        paths = [Path(p) for p in args.inputs]
    else:
        paths = sorted(REPO_ROOT.glob("*.md"))
        if not paths:
            sys.exit("No Markdown files given and none found in the repository root.")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    first_page = None

    for md_path in paths:
        if not md_path.is_file():
            print("skip   %s (not a file)" % md_path, file=sys.stderr)
            failures += 1
            continue

        html, mode = build_page(md_path, args)
        html_path = out_dir / (md_path.stem + ".github.html")
        html_path.write_text(html, encoding="utf-8")
        print("wrote  %s  (%.1f KB, mode=%s)" % (html_path, html_path.stat().st_size / 1024, mode))
        if first_page is None:
            first_page = html_path

    if first_page is not None and not args.no_open:
        webbrowser.open(first_page.resolve().as_uri())

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
