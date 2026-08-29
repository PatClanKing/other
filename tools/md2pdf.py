#!/usr/bin/env python3
"""Render Markdown files to PDF from inside a self contained virtual environment.

Two rendering engines are supported, tried in this order when --engine is "auto":

  1. weasyprint  Best output (real page boxes, proper CSS). Needs native Pango
                 and Cairo libraries, which are extra work to install on Windows.
  2. xhtml2pdf   Pure Python, installs from pip alone, works everywhere. Slightly
                 plainer output but perfectly readable.

Usage:
    python tools/md2pdf.py github-ssh-setup.md
    python tools/md2pdf.py *.md --toc -o build
    python tools/md2pdf.py doc.md --engine xhtml2pdf --page-size Letter
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_CSS = HERE / "style.css"
DEFAULT_OUT_DIR = HERE / "out"

MD_EXTENSIONS = [
    "extra",        # tables, fenced code, footnotes, attr_list, def_list, abbr
    "admonition",
    "codehilite",
    "sane_lists",
    "toc",
]
MD_EXTENSION_CONFIG = {
    "codehilite": {"guess_lang": False, "noclasses": False},
    "toc": {"permalink": False},
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
{footer}{toc}{body}
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# Engine specific page geometry
# --------------------------------------------------------------------------- #

def weasyprint_page_css(page_size: str, margin_mm: float) -> str:
    return f"""
@page {{
    size: {page_size};
    margin: {margin_mm}mm;
    @bottom-center {{
        content: counter(page) " / " counter(pages);
        font-size: 8pt;
        color: #6b7683;
    }}
}}
#footerContent {{ display: none; }}
"""


def xhtml2pdf_page_css(page_size: str, margin_mm: float) -> str:
    # xhtml2pdf needs an explicit named frame that the footer div is pinned to.
    footer_bottom = max(margin_mm - 12.0, 4.0)
    return f"""
@page {{
    size: {page_size.lower()} portrait;
    margin: {margin_mm}mm;
    @frame footer_frame {{
        -pdf-frame-content: footerContent;
        left: {margin_mm}mm;
        right: {margin_mm}mm;
        bottom: {footer_bottom}mm;
        height: 10mm;
    }}
}}
"""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def pygments_css() -> str:
    """Syntax highlighting rules for fenced code blocks, if Pygments is present."""
    try:
        from pygments.formatters import HtmlFormatter
    except ImportError:
        return ""
    return HtmlFormatter(style="friendly").get_style_defs(".codehilite")


def first_heading(markdown_text: str, fallback: str) -> str:
    for line in markdown_text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1)
    return fallback


def available_engines() -> list:
    """Engines that can actually be imported right now, best first."""
    found = []
    try:
        import weasyprint  # noqa: F401
        found.append("weasyprint")
    except Exception:
        pass
    try:
        import xhtml2pdf.pisa  # noqa: F401
        found.append("xhtml2pdf")
    except Exception:
        pass
    return found


def build_html(md_path: Path, args: argparse.Namespace, engine: str):
    try:
        import markdown
    except ImportError:
        sys.exit(
            "The 'markdown' package is missing. Activate the virtual environment "
            "and run: pip install -r tools/requirements.txt"
        )

    text = md_path.read_text(encoding="utf-8")
    title = args.title or first_heading(text, md_path.stem)

    converter = markdown.Markdown(
        extensions=MD_EXTENSIONS,
        extension_configs=MD_EXTENSION_CONFIG,
    )
    body = converter.convert(text)

    # A document maintained by tools/update_toc.py already carries its own contents list.
    # Generating a second one here would print it twice, so defer to the one in the file.
    has_own_toc = "<!-- toc -->" in text

    toc_html = ""
    if args.toc and has_own_toc:
        print(
            "       note: %s has its own table of contents, so --toc was skipped."
            % md_path.name,
            file=sys.stderr,
        )
    elif args.toc:
        toc_body = getattr(converter, "toc", "")
        if toc_body.strip():
            toc_html = (
                '<div class="toc-block">\n'
                '<div class="toc-heading">Contents</div>\n'
                + toc_body
                + "\n</div>\n"
            )

    css_path = Path(args.css) if args.css else DEFAULT_CSS
    base_css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    if engine == "weasyprint":
        page_css = weasyprint_page_css(args.page_size, args.margin)
        footer = ""
    else:
        page_css = xhtml2pdf_page_css(args.page_size, args.margin)
        footer = (
            '<div id="footerContent">'
            "<pdf:pagenumber> / <pdf:pagecount>"
            "</div>\n"
        )

    css = "\n".join([page_css, base_css, pygments_css()])
    html = HTML_TEMPLATE.format(
        lang=args.lang,
        title=title,
        css=css,
        footer=footer,
        toc=toc_html,
        body=body,
    )
    return html, title


def render_weasyprint(html: str, out_path: Path, base_dir: Path) -> None:
    from weasyprint import HTML

    HTML(string=html, base_url=str(base_dir)).write_pdf(str(out_path))


def render_xhtml2pdf(html: str, out_path: Path, base_dir: Path) -> None:
    from xhtml2pdf import pisa

    def link_callback(uri: str, rel: str) -> str:
        """Resolve relative image and asset paths against the Markdown file."""
        if uri.startswith(("http://", "https://", "data:")):
            return uri
        candidate = (base_dir / uri).resolve()
        return str(candidate) if candidate.exists() else uri

    with out_path.open("wb") as handle:
        result = pisa.CreatePDF(
            src=html,
            dest=handle,
            encoding="utf-8",
            link_callback=link_callback,
        )
    if result.err:
        raise RuntimeError("xhtml2pdf reported %s error(s)" % result.err)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="md2pdf.py",
        description="Convert Markdown files to PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Markdown files to convert. Defaults to every .md file in the repository root.",
    )
    parser.add_argument(
        "-o", "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="Directory for the generated PDFs (default: tools/out).",
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "weasyprint", "xhtml2pdf"],
        default="auto",
        help="PDF backend. 'auto' prefers weasyprint and falls back to xhtml2pdf.",
    )
    parser.add_argument("--css", help="Override stylesheet (default: tools/style.css).")
    parser.add_argument("--title", help="Document title. Defaults to the first H1 heading.")
    parser.add_argument("--toc", action="store_true", help="Insert a table of contents.")
    parser.add_argument("--page-size", default="A4", help="Page size, for example A4 or Letter.")
    parser.add_argument("--margin", type=float, default=20.0, help="Page margin in millimetres.")
    parser.add_argument("--lang", default="en", help="Document language attribute.")
    parser.add_argument("--keep-html", action="store_true", help="Also write the intermediate HTML.")
    parser.add_argument("--list-engines", action="store_true", help="Show installed engines and exit.")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    installed = available_engines()
    if args.list_engines:
        print("Installed engines (best first):")
        for name in ["weasyprint", "xhtml2pdf"]:
            state = "available" if name in installed else "not installed"
            print("  %-12s %s" % (name, state))
        return 0

    if not installed:
        sys.exit(
            "No PDF engine is installed. Activate the virtual environment and run:\n"
            "  pip install -r tools/requirements.txt"
        )

    if args.engine == "auto":
        engine = installed[0]
    elif args.engine in installed:
        engine = args.engine
    else:
        sys.exit(
            "Engine '%s' is not installed. Available: %s"
            % (args.engine, ", ".join(installed))
        )

    if args.inputs:
        paths = [Path(p) for p in args.inputs]
    else:
        paths = sorted(REPO_ROOT.glob("*.md"))
        if not paths:
            sys.exit("No Markdown files given and none found in the repository root.")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for md_path in paths:
        if not md_path.is_file():
            print("skip   %s (not a file)" % md_path, file=sys.stderr)
            failures += 1
            continue

        html, title = build_html(md_path, args, engine)
        out_path = out_dir / (md_path.stem + ".pdf")

        if args.keep_html:
            html_path = out_dir / (md_path.stem + ".html")
            html_path.write_text(html, encoding="utf-8")
            print("wrote  %s" % html_path)

        try:
            if engine == "weasyprint":
                render_weasyprint(html, out_path, md_path.resolve().parent)
            else:
                render_xhtml2pdf(html, out_path, md_path.resolve().parent)
        except Exception as exc:
            print("FAILED %s via %s: %s" % (md_path, engine, exc), file=sys.stderr)
            failures += 1
            continue

        size_kb = out_path.stat().st_size / 1024
        print("wrote  %s  (%.1f KB, engine=%s, title=%r)" % (out_path, size_kb, engine, title))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
