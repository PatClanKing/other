# tools

Markdown to PDF generation, driven by a Python virtual environment that lives inside this folder.
Nothing is installed globally and nothing outside `tools/.venv` is touched.

---

## 1. What is here

1. `make-pdf.bat` Click to run. Sets up the environment if needed, then converts.
2. `preview-github.bat` Click to run. Opens a GitHub accurate preview in your browser.
3. `md2pdf.py` The converter. Reads Markdown, renders HTML, writes PDF.
4. `github_preview.py` Renders Markdown the way github.com does.
5. `update_toc.py` Generates or refreshes a table of contents in a Markdown file.
6. `scrub_pii.py` Finds and removes identifying information before publishing.
7. `check_intros.py` Finds code blocks and tables that nothing introduced.
8. `reflow_prose.py` Joins hard wrapped prose so GitHub does not break it mid sentence.
9. `style.css` Print stylesheet. Edit this to change fonts, colours and spacing.
10. `requirements.txt` Core dependencies. Pure Python, installs from pip alone.
11. `requirements-weasyprint.txt` Optional higher quality engine.
12. `setup.ps1` One shot environment setup for PowerShell.
13. `setup.sh` One shot environment setup for Git Bash, macOS and Linux.
14. `out/` Generated PDFs. Ignored by Git.
15. `.venv/` The virtual environment. Ignored by Git.

---

## 2. Easiest route: `make-pdf.bat`

Double click `tools\make-pdf.bat` in Explorer. That is the whole procedure.

On the first run it creates `tools\.venv` and installs the dependencies, which takes about a
minute. Every run after that finishes in a second or two. When it is done, the output folder
opens automatically.

### 2.1 Four ways to invoke it

| Way | What happens |
| :--- | :--- |
| Double click it in Explorer | Converts every `.md` file in the repository root |
| Drag `.md` files onto it | Converts only the files you dropped |
| `tools\make-pdf.bat doc.md` | Converts the named file |
| `tools\make-pdf.bat /nopause doc.md` | Same, but no key press prompt and no Explorer popup, for scripts |

It exits `0` on success and `1` on failure, so it is safe to call from other scripts.

### 2.2 Changing the options it uses

The batch file passes `--toc` by default. Edit this one line near the top to change that:

```bat
set "OPTIONS=--toc"
```

Any flag from section 8 works there, for example `set "OPTIONS=--toc --page-size Letter"`.

---

## 3. Manual route

Useful on macOS and Linux, or when you want to pass one off flags.

### 3.1 PowerShell

```powershell
.\tools\setup.ps1
.\tools\.venv\Scripts\python.exe tools\md2pdf.py github-ssh-setup.md --toc
```

### 3.2 Git Bash

```bash
bash tools/setup.sh
tools/.venv/Scripts/python.exe tools/md2pdf.py github-ssh-setup.md --toc
```

### 3.3 macOS and Linux

```bash
bash tools/setup.sh
tools/.venv/bin/python tools/md2pdf.py github-ssh-setup.md --toc
```

The PDF lands in `tools/out/github-ssh-setup.pdf`.

Calling the interpreter inside `.venv` by its full path means you never have to activate anything.
If you prefer an activated shell:

```bash
source tools/.venv/Scripts/activate
```

```powershell
.\tools\.venv\Scripts\Activate.ps1
```

---

## 4. Table of contents

GitHub shows an outline behind the hamburger icon at the top right of a rendered `.md`
file, but it is hidden behind a click and it does not survive export to PDF. `update_toc.py`
writes a real one into the file, between `<!-- toc -->` markers so re-running it replaces
the block rather than stacking copies.

```bash
tools/.venv/Scripts/python.exe tools/update_toc.py github-ssh-setup.md
```

Useful flags:

1. `--depth 2` lists top level sections only. The default of 3 also lists steps.
2. `--check` reports whether the block is stale and exits 1, without writing. Handy in a
   pre commit hook.

Anchors follow GitHub's slug rule, and `github_preview.py` adds matching `id` attributes
to every heading, so the links work in the preview as well as on github.com. `md2pdf.py`
detects a document that already has its own contents and skips its `--toc` flag, so you
never get two.

---

## 5. Removing identifying information

A runbook written on one machine is read on many, and personal detail leaks in through
example commands almost by accident. Git history is permanent, so catching it before the
first commit is much cheaper than catching it after.

```bash
tools/.venv/Scripts/python.exe tools/scrub_pii.py github-ssh-setup.md --check
```

The script splits findings into two categories, because they need different handling:

1. **Replaced automatically.** Email addresses become `<email>`, the username inside a
   home directory path becomes `<username>`, machine names become `<hostname>`. Addresses
   belonging to a service rather than a person are left alone, so `git@github.com`
   survives.
2. **Reported for a human decision, never changed.** Key fingerprints, public key blobs,
   tokens and IP addresses. This matters: `github-ssh-setup.md` quotes GitHub's three
   published host key fingerprints, and scrubbing those would break its verification step.
   A token is a live secret, and the right response is revoking it, not hiding it.

Flags:

1. `--check` reports without writing and exits 1 if anything would be replaced, so it
   works in a pre commit hook.
2. `--extra "Name=<placeholder>"` adds a literal substitution for anything project
   specific, such as a repository owner or an employer.
3. `--quiet-review` suppresses the second category once you have read it.

---

## 6. Two defects the Markdown source hides

Both of these look fine while you read the `.md` file and are obvious on the rendered
page, which is why they need a check rather than an eye.

### 6.1 Blocks and tables nobody introduced

A heading followed straight into a fenced command names the step without saying what the
command does or what the reader should see afterwards.

```bash
tools/.venv/Scripts/python.exe tools/check_intros.py github-ssh-setup.md
```

It reports every fenced block and table whose preceding line is a heading, a horizontal
rule, another fence or a table row, and exits 1 if it finds any. Prose, a list item or a
bold `**Run from:**` line all count as a proper introduction.

### 6.2 Hard wrapped paragraphs

GitHub Flavored Markdown turns a single newline inside a paragraph into a `<br>`. Prose
wrapped at 100 columns in an editor therefore renders with ragged breaks mid sentence, at
the author's width rather than the reader's.

```bash
tools/.venv/Scripts/python.exe tools/reflow_prose.py github-ssh-setup.md --check
```

Drop `--check` to join them into one source line per paragraph. Fenced code blocks,
tables, headings, rules and Markdown's deliberate hard break syntax (two trailing spaces,
or a backslash) are all left alone.

---

## 7. Engine options, ranked

| Rank | Engine | Install cost | Output quality | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `xhtml2pdf` | `pip install` only, zero native libraries | Good. Correct tables, code blocks, page numbers | Default. Recommended on Windows |
| 2 | `weasyprint` | Needs GTK (Pango, Cairo) installed system wide | Best. Real CSS page boxes, superior line breaking | Worth it if you already have GTK |

`md2pdf.py --engine auto` prefers WeasyPrint when it imports cleanly and silently falls back to
xhtml2pdf otherwise, so the same command works on every machine.

To add the optional engine:

```bash
bash tools/setup.sh --weasyprint
```

Check what is currently usable:

```bash
tools/.venv/Scripts/python.exe tools/md2pdf.py --list-engines
```

---

## 8. Command reference

```
python tools/md2pdf.py [inputs...] [options]
```

| Option | Default | Meaning |
| :--- | :--- | :--- |
| `inputs` | every `.md` in the repository root | Markdown files to convert |
| `-o`, `--out-dir` | `tools/out` | Where the PDFs are written |
| `--engine` | `auto` | `auto`, `weasyprint` or `xhtml2pdf` |
| `--css` | `tools/style.css` | Alternative stylesheet |
| `--title` | first `#` heading | Document title used in PDF metadata |
| `--toc` | off | Insert a table of contents at the front |
| `--page-size` | `A4` | For example `A4` or `Letter` |
| `--margin` | `20` | Page margin in millimetres |
| `--lang` | `en` | Document language attribute |
| `--keep-html` | off | Also write the intermediate HTML for debugging |
| `--list-engines` | off | Report which engines are installed, then exit |

### 8.1 Examples

Convert every Markdown file in the repository root:

```bash
tools/.venv/Scripts/python.exe tools/md2pdf.py
```

US Letter with wider margins and a contents page:

```bash
tools/.venv/Scripts/python.exe tools/md2pdf.py github-ssh-setup.md --toc --page-size Letter --margin 25
```

Inspect the generated HTML when something looks wrong:

```bash
tools/.venv/Scripts/python.exe tools/md2pdf.py github-ssh-setup.md --keep-html
```

---

## 9. Markdown features supported

1. Tables, fenced code blocks, footnotes, definition lists, abbreviations (`extra`).
2. Syntax highlighting via Pygments (`codehilite`).
3. Admonition blocks.
4. Heading anchors and the generated table of contents (`toc`).
5. Nested numbered lists that keep their own numbering (`sane_lists`).

---

## 10. Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `Python was not found` when running the batch file | No interpreter on PATH | Install Python 3.9 or newer and tick "Add python.exe to PATH" |
| `No PDF engine is installed` | Setup was never run, or the wrong interpreter is being used | Run the batch file or a setup script, then call the interpreter under `tools/.venv` |
| `Engine 'weasyprint' is not installed` | GTK libraries missing, so the import fails | Use `--engine xhtml2pdf`, or install GTK and rerun setup with `--weasyprint` |
| Fonts look wrong in code blocks | DejaVu Sans Mono is not present | Edit the font stacks in `style.css` |
| Environment is in a bad state | Partial or interrupted install | Delete `tools\.venv` and run the batch file again, or `bash tools/setup.sh --force` |
| `execution of scripts is disabled` in PowerShell | Execution policy blocks `setup.ps1` | Use `make-pdf.bat` instead, or run once: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |

---

## 11. Verified result

`github-ssh-setup.md` renders to a 19 page A4 PDF of roughly 76 KB using the
default `xhtml2pdf` engine, with its own contents list, syntax highlighted code blocks, styled
tables and `page / total` footers.
