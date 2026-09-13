# tools

GitHub accurate Markdown previewing, plus the three linters that check a document before it is pushed. Everything runs from a Python virtual environment that lives inside this folder, so nothing is installed globally and nothing outside `tools/.venv` is touched.

The only output these tools produce is HTML. Code blocks in that HTML carry GitHub's copy button, which is the reason the previous PDF pipeline was removed: a PDF cannot have one.

---

<!-- toc -->

## Contents

* [1. What is here](#1-what-is-here)
* [2. Easiest route: `preview-github.bat`](#2-easiest-route-preview-githubbat)
  * [2.1 Four ways to invoke it](#21-four-ways-to-invoke-it)
* [3. Manual route](#3-manual-route)
  * [3.1 Git Bash](#31-git-bash)
  * [3.2 PowerShell](#32-powershell)
  * [3.3 macOS and Linux](#33-macos-and-linux)
* [4. How the preview works](#4-how-the-preview-works)
* [5. Table of contents](#5-table-of-contents)
* [6. Removing identifying information](#6-removing-identifying-information)
* [7. Two defects the Markdown source hides](#7-two-defects-the-markdown-source-hides)
  * [7.1 Blocks and tables nobody introduced](#71-blocks-and-tables-nobody-introduced)
  * [7.2 Hard wrapped paragraphs](#72-hard-wrapped-paragraphs)
* [8. Command reference](#8-command-reference)
  * [8.1 Examples](#81-examples)
* [9. Troubleshooting](#9-troubleshooting)
* [10. Verified result](#10-verified-result)

<!-- /toc -->

---

## 1. What is here

Ten files do the work, and two generated directories hold the results:

1. `preview-github.bat` Click to run. Opens a GitHub accurate preview in your browser.
2. `github_preview.py` Renders Markdown the way github.com does, with a copy button on every code block.
3. `update_toc.py` Generates or refreshes a table of contents in a Markdown file.
4. `scrub_pii.py` Finds and removes identifying information before publishing.
5. `check_intros.py` Finds code blocks and tables that nothing introduced.
6. `reflow_prose.py` Joins hard wrapped prose so GitHub does not break it mid sentence.
7. `assets/github-markdown.css` GitHub's own stylesheet, vendored so the preview works offline.
8. `requirements.txt` Dependencies. Pure Python, installs from pip alone.
9. `setup.sh` One shot environment setup for Git Bash, macOS and Linux.
10. `setup.ps1` One shot environment setup for PowerShell.
11. `out/` Generated previews. Ignored by Git.
12. `.venv/` The virtual environment. Ignored by Git.

---

## 2. Easiest route: `preview-github.bat`

Double click `tools\preview-github.bat` in Explorer. That is the whole procedure.

On the first run it creates `tools\.venv` and installs the dependencies, which takes a few seconds. Every run after that is close to instant. When it is done, the preview opens in your default browser.

### 2.1 Four ways to invoke it

Each row is a different way to start the same script, and the second column says which files it will render:

| Way | What happens |
| :--- | :--- |
| Double click it in Explorer | Previews every `.md` file in the repository root |
| Drag `.md` files onto it | Previews only the files you dropped |
| `tools\preview-github.bat doc.md` | Previews the named file |
| `tools\preview-github.bat /offline` | Renders locally, with no network call |
| `tools\preview-github.bat /nopause` | No key press prompt and no browser window, for scripts |

It exits `0` on success and `1` on failure, so it is safe to call from other scripts.

---

## 3. Manual route

Useful when you want to pass one off flags, or when you are not on Windows. Run the setup script once, then call the interpreter inside `.venv` by its full path, which means you never have to activate anything.

### 3.1 Git Bash

Create the environment:

```bash
bash tools/setup.sh
```

Then render:

```bash
tools/.venv/Scripts/python.exe tools/github_preview.py github-ssh-setup.md
```

### 3.2 PowerShell

Create the environment:

```powershell
.\tools\setup.ps1
```

Then render:

```powershell
.\tools\.venv\Scripts\python.exe tools\github_preview.py github-ssh-setup.md
```

### 3.3 macOS and Linux

The same setup script works, and only the path to the interpreter differs:

```bash
bash tools/setup.sh
```

Then render:

```bash
tools/.venv/bin/python tools/github_preview.py github-ssh-setup.md
```

The preview lands in `tools/out/github-ssh-setup.github.html`.

---

## 4. How the preview works

`github_preview.py` has two rendering modes, and the difference matters if the document is confidential.

| Mode | How it renders | Network | Accuracy |
| :--- | :--- | :--- | :--- |
| `api`, the default | Posts the Markdown to <https://api.github.com/markdown> with mode `gfm` | Yes, the document is sent to GitHub to be rendered | Exact, because it is GitHub's own renderer |
| `--offline` | Renders locally with `python-markdown` and `nl2br` | None | Close, not exact |

Three things are worth knowing about it:

1. **The document is sent to GitHub in the default mode.** It is rendered and returned, not stored or published, but use `--offline` if that matters to you. The offline mode is also used automatically whenever the API call fails.
2. **The rate limit is 60 calls an hour** without authentication. Set a `GITHUB_TOKEN` environment variable to raise that to 5000.
3. **Two things are added that GitHub's API does not return.** Heading `id` attributes, without which a contents block links to nothing in the preview, and the copy button, which on github.com comes from their web app rather than from the Markdown renderer.

The copy button uses the asynchronous clipboard API where it is available and falls back to a hidden textarea and `execCommand` where it is not. Copying needs a genuine user gesture, so an automated browser usually denies it outright, which means this is the one feature that has to be checked by hand.

---

## 5. Table of contents

GitHub shows an outline behind the hamburger icon at the top right of a rendered `.md` file, but it is hidden behind a click. `update_toc.py` writes a real one into the file, between `<!-- toc -->` markers so rerunning it replaces the block rather than stacking copies.

```bash
tools/.venv/Scripts/python.exe tools/update_toc.py github-ssh-setup.md
```

Two flags are worth knowing:

1. `--depth 2` lists top level sections only. The default of 3 also lists steps.
2. `--check` reports whether the block is stale and exits 1, without writing. Handy in a pre commit hook.

Anchors follow GitHub's slug rule, and `github_preview.py` adds matching `id` attributes to every heading, so the links work in the preview as well as on github.com. Inline code in a heading is kept in the contents entry rather than flattened, because stripping the backticks off a name such as `ssh-agent` would put a bare hyphenated word back into prose. The anchor ignores the backticks either way.

---

## 6. Removing identifying information

A runbook written on one machine is read on many, and personal detail leaks in through example commands almost by accident. Git history is permanent, so catching it before the first commit is much cheaper than catching it after.

```bash
tools/.venv/Scripts/python.exe tools/scrub_pii.py github-ssh-setup.md --check
```

The script splits findings into two categories, because they need different handling:

1. **Replaced automatically.** Email addresses become `<email>`, the username inside a home directory path becomes `<username>`, machine names become `<hostname>`. Addresses belonging to a service rather than a person are left alone, so `git@github.com` survives.
2. **Reported for a human decision, never changed.** Key fingerprints, public key blobs, tokens and IP addresses. This matters: `github-ssh-setup.md` quotes GitHub's three published host key fingerprints, and scrubbing those would break its verification step. A token is a live secret, and the right response is revoking it, not hiding it.

Three flags control it:

1. `--check` reports without writing and exits 1 if anything would be replaced, so it works in a pre commit hook.
2. `--extra "Name=<placeholder>"` adds a literal substitution for anything project specific, such as a repository owner or an employer.
3. `--quiet-review` suppresses the second category once you have read it.

---

## 7. Two defects the Markdown source hides

Both of these look fine while you read the `.md` file and are obvious on the rendered page, which is why they need a check rather than an eye.

### 7.1 Blocks and tables nobody introduced

A heading followed straight into a fenced command names the step without saying what the command does or what the reader should see afterwards.

```bash
tools/.venv/Scripts/python.exe tools/check_intros.py github-ssh-setup.md
```

It reports every fenced block and table whose preceding line is a heading, a horizontal rule, another fence or a table row, and exits 1 if it finds any. Prose, a list item or a bold `**Run from:**` line all count as a proper introduction.

### 7.2 Hard wrapped paragraphs

GitHub Flavored Markdown turns a single newline inside a paragraph into a `<br>`. Prose wrapped at 100 columns in an editor therefore renders with ragged breaks mid sentence, at the author's width rather than the reader's.

```bash
tools/.venv/Scripts/python.exe tools/reflow_prose.py github-ssh-setup.md --check
```

Drop `--check` to join them into one source line per paragraph. Fenced code blocks, tables, headings, rules and Markdown's deliberate hard break syntax (two trailing spaces, or a backslash) are all left alone.

---

## 8. Command reference

The preview script takes one or more files and a handful of flags:

```
python tools/github_preview.py [inputs...] [options]
```

Every option, with the value used when you leave it out:

| Option | Default | Meaning |
| :--- | :--- | :--- |
| `inputs` | every `.md` in the repository root | Markdown files to render |
| `-o`, `--out-dir` | `tools/out` | Where the HTML is written |
| `--offline` | off | Render locally, with no network call |
| `--context` | none | Repository for resolving `#123` and `@user` links, as `<owner>/<repo>` |
| `--no-open` | off | Do not open the preview in a browser |

### 8.1 Examples

Render every Markdown file in the repository root:

```bash
tools/.venv/Scripts/python.exe tools/github_preview.py
```

Render one file without sending it anywhere:

```bash
tools/.venv/Scripts/python.exe tools/github_preview.py github-ssh-setup.md --offline
```

Render into a chosen directory without opening a browser, which is the form to use from a script:

```bash
tools/.venv/Scripts/python.exe tools/github_preview.py github-ssh-setup.md -o build --no-open
```

---

## 9. Troubleshooting

Find the symptom in the first column, then apply the fix:

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `Python was not found` when running the batch file | No interpreter on PATH | Install Python 3.9 or newer and tick "Add python.exe to PATH" |
| `tools/setup.sh: line N: $'\r': command not found` | The script was checked out with Windows line endings | `.gitattributes` pins `*.sh` to `eol=lf`, so refresh the working copy: `rm tools/setup.sh` then `git checkout tools/setup.sh` |
| `API rate limit exceeded` | More than 60 unauthenticated calls in an hour | Set `GITHUB_TOKEN`, or use `--offline` |
| The preview is subtly different from github.com | The API call failed, so it fell back to offline rendering | Check the mode reported in the output line, and rerun when the network is back |
| Contents links go nowhere in the preview | Stale contents block | Run `update_toc.py`, which is also what `--check` reports |
| The copy button does nothing | The page is open from a `file://` path in a browser that restricts the clipboard API | The textarea fallback covers most cases. Serve the file over `http://localhost` if a browser refuses both |
| Environment is in a bad state | Partial or interrupted install | Delete `tools\.venv` and run the batch file again, or `bash tools/setup.sh --force` |
| `execution of scripts is disabled` in PowerShell | Execution policy blocks `setup.ps1` | Use `preview-github.bat` instead, or run once: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |

---

## 10. Verified result

`github-ssh-setup.md` renders to a single self contained HTML file of roughly 91 KB, with GitHub's stylesheet inlined, no external assets, heading anchors that match the generated contents block, and a copy button on each of its 87 code blocks. It opens correctly from a local file path with no network access.
