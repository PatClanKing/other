# Technical runbooks

Practical, copy pasteable guides, each one written to be followed start to finish in a single sitting, plus the small toolchain that renders and checks them.

Every guide targets Git Bash on Windows.

---

## Guides

| Guide | What you get | Read it |
| :--- | :--- | :--- |
| GitHub SSH setup | An SSH key, loaded into a shared `ssh-agent` that starts with every terminal, registered with GitHub, with the whole chain verified | [Markdown](docs/github-ssh-setup.md) or [rendered](docs/github-ssh-setup.html) |

---

## Layout

Each document lives in `docs/` with its rendered HTML and its figures beside it:

```text
docs/
  github-ssh-setup.md        the source
  github-ssh-setup.html      generated, committed, and what people actually read
  figures/
    ssh-auth-flow.py         the diagram's source of truth
    ssh-auth-flow.drawio     editable draw.io file
    ssh-auth-flow.drawio.svg the committed artifact, a picture carrying its own source
    ssh-auth-flow.png        raster copy, for pasting elsewhere
tools/
  github_preview.py          renders Markdown the way github.com does
  github_preview.bat         click to run, for Windows
  lint/                      the four checks every document has to pass
  setup.sh, setup.ps1        one shot environment setup
```

The HTML is generated but tracked on purpose, because it is the version people read and it carries a copy button on every code block. It is written beside its Markdown, since the page points at its figures by a relative path.

---

## Rendering a guide

On Windows, double click `tools\github_preview.bat`. From a terminal, set the environment up once:

```bash
bash tools/setup.sh
```

Then render, which writes the HTML next to the Markdown and opens it:

```bash
tools/.venv/bin/python tools/github_preview.py docs/github-ssh-setup.md
```

Add `--offline` to render locally with no network call, which is what to use if a document is confidential. Full detail is in [tools/README.md](tools/README.md).

---

## House style

The conventions every guide follows, and the reasoning behind each one, are in [CLAUDE.md](CLAUDE.md). The short version is that a step's number is its section number, every command block holds one command and is introduced by a line of prose saying what it does, acronyms are expanded at first use with the glossary at the end, prose carries no dashes, and nothing identifying ever gets committed.

The four checks in `tools/lint/` enforce the mechanical half of that, and they are the gate before anything is published.
