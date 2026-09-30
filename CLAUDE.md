# CLAUDE.md

Guidance for working in this repository.

## Always regenerate the HTML with the Markdown

`docs/github-ssh-setup.html` is a generated artifact, and it is the form of the document that actually gets read. It is **not** updated automatically.

Whenever you change `github-ssh-setup.md`, regenerate the HTML in the same turn, before reporting the work as done:

```bash
tools/.venv/bin/python tools/github_preview.py docs/github-ssh-setup.md --offline
```

Never hand back a change to the Markdown without the matching HTML. Treat the two as one deliverable, and commit them together: the HTML is tracked, so a commit touching only the Markdown leaves the published document stale. The same applies to any other document in `docs/`.

The HTML is written beside its Markdown, and figures are folded into it as data URIs, so the result is one portable file that works anywhere with nothing beside it. `--link-assets` reverses that for a smaller file that only works next to its `figures/` folder.

On Windows the interpreter is `tools/.venv/Scripts/python.exe`. If `tools/.venv` does not exist, create it with `bash tools/setup.sh` first.

## Figures

A figure's source of truth is its Python script in `docs/figures/`, never the `.drawio` file. Opening a generated `.drawio` in the draw.io GUI and nudging a box is lost on the next build. Rebuild with the `umldrawer` skill, from inside `docs/figures`:

```bash
umldrawer build ssh-auth-flow.py
```

```bash
umldrawer png ssh-auth-flow.drawio.svg 1800
```

That second command writes `ssh-auth-flow.preview.png`, so rename it to `ssh-auth-flow.png` to match what the repository uses. Always look at the render before believing it: neither router avoids obstacles, so a line straight through a box passes every automated check.

The document references the `.drawio.svg`, not the `.png`, because that file is a picture carrying its own editable source and the two therefore cannot drift apart.

## Before saying a document change is finished

Run all four linters. They are the gate, and a failure is a defect until you have read it and decided otherwise:

```bash
tools/.venv/bin/python tools/lint/update_toc.py docs/github-ssh-setup.md
```

```bash
tools/.venv/bin/python tools/lint/check_intros.py docs/github-ssh-setup.md
```

```bash
tools/.venv/bin/python tools/lint/reflow_prose.py docs/github-ssh-setup.md --check
```

```bash
tools/.venv/bin/python tools/lint/scrub_pii.py docs/github-ssh-setup.md --check
```

Regenerate the contents block after any structural edit rather than editing it by hand, and check that every `](#anchor)` link still resolves to a heading. Changing a heading changes its anchor, so links and the contents block both have to be rebuilt.

## House style for the documents

The full style is in the `technical-runbook` skill. The rules that get broken most often:

1. **No dashes in prose.** Not in sentences, list items, ranges or compound adjectives. A hyphenated program name goes in a code span, so `ssh-agent` rather than the bare word. Fenced blocks, inline code, file paths, URLs and table separator rows are exempt.
2. **A step's number is its section number.** Never write "Step N" in a heading, because `3.4` already is step 4.
3. **One command per fenced block**, each introduced by a line of prose saying what it does or what the reader should see next. The verification checklist is the one deliberate exception.
4. **One source line per paragraph.** Do not hard wrap, because a single newline inside a paragraph renders as a `<br>` on GitHub.
5. **Expand every acronym at first use**, and keep the glossary at the end complete and alphabetical.
6. **No identifying information.** Use `<email>`, `<username>`, `<hostname>`, `<owner>/<repo>`. Service addresses such as `git@github.com` stay as they are.

## Scope of the runbook

`docs/github-ssh-setup.md` targets Git Bash on Windows. Do not add macOS or Linux variants of commands; the opening paragraph states the scope deliberately. Windows specific tooling such as `clip.exe`, `winpty`, `MSYS_NO_PATHCONV` and `/c/...` drive paths is expected and correct.

Refer to the OpenSSH agent as `ssh-agent` in a code span, not as "the agent". The exception is a password manager's own SSH agent, such as 1Password or Bitwarden, which is a different thing.

## Tooling

HTML preview is the only output. There is no PDF pipeline, and a PDF cannot carry GitHub's copy button, which is why it was removed. Do not reintroduce one.

Never paste a URL you have not fetched, and re verify any value quoted from upstream rather than trusting it. The three GitHub host key fingerprints in the runbook must match <https://api.github.com/meta>.

Commands in the runbook are a promise that those exact lines work. Run a command before documenting it, or say plainly that it is untested.
