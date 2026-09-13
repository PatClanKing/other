#!/usr/bin/env bash
# Create the Python virtual environment for the Markdown preview tool.
# Works in Git Bash on Windows, and on macOS and Linux.
#
#   bash tools/setup.sh         # install the dependencies
#   bash tools/setup.sh --force # rebuild the virtual environment from scratch
#
# Afterwards:
#   source tools/.venv/Scripts/activate   # Git Bash on Windows
#   source tools/.venv/bin/activate       # macOS and Linux
#   python tools/github_preview.py github-ssh-setup.md

set -euo pipefail

TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$TOOLS_DIR/.venv"

FORCE=0
for arg in "$@"; do
    case "$arg" in
        --force)   FORCE=1 ;;
        -h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *)         echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

# Locate an interpreter. On Windows the py launcher is the most reliable.
if command -v py >/dev/null 2>&1; then
    BOOTSTRAP_PY="py -3"
elif command -v python3 >/dev/null 2>&1; then
    BOOTSTRAP_PY="python3"
elif command -v python >/dev/null 2>&1; then
    BOOTSTRAP_PY="python"
else
    echo "No Python interpreter found. Install Python 3.9 or newer and retry." >&2
    exit 1
fi

# Windows venvs put the interpreter in Scripts/, POSIX venvs in bin/.
if [ -x "$VENV_DIR/Scripts/python.exe" ]; then
    VENV_PY="$VENV_DIR/Scripts/python.exe"
else
    VENV_PY="$VENV_DIR/bin/python"
fi

if [ "$FORCE" -eq 1 ] && [ -d "$VENV_DIR" ]; then
    echo "Removing existing virtual environment at $VENV_DIR"
    rm -rf "$VENV_DIR"
fi

if [ ! -x "$VENV_PY" ]; then
    echo "Creating virtual environment in $VENV_DIR"
    # shellcheck disable=SC2086
    $BOOTSTRAP_PY -m venv "$VENV_DIR"
    if [ -x "$VENV_DIR/Scripts/python.exe" ]; then
        VENV_PY="$VENV_DIR/Scripts/python.exe"
    else
        VENV_PY="$VENV_DIR/bin/python"
    fi
else
    echo "Reusing existing virtual environment in $VENV_DIR"
fi

echo "Upgrading pip"
"$VENV_PY" -m pip install --upgrade pip --quiet

echo "Installing from $TOOLS_DIR/requirements.txt"
"$VENV_PY" -m pip install -r "$TOOLS_DIR/requirements.txt"

echo
echo "Done. Next steps:"
if [ -x "$VENV_DIR/Scripts/python.exe" ]; then
    echo "  source tools/.venv/Scripts/activate"
else
    echo "  source tools/.venv/bin/activate"
fi
echo "  python tools/github_preview.py github-ssh-setup.md"
