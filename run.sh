#!/usr/bin/env bash
# Operator — Ferry, Cargo & ACMI
# macOS and Linux launcher. Double-click, or run ./run.sh from a terminal.
set -e
cd "$(dirname "$0")"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  cat <<'MSG'

  Python 3.10 or newer is required.

    macOS : install from https://www.python.org/downloads/macos/
            (or "brew install python" if you use Homebrew)
    Linux : sudo apt install python3 python3-venv     (Debian/Ubuntu)

  Then run this file again.

MSG
  exit 1
fi

if ! "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
  echo "Python 3.10 or newer is required (found $("$PY" -V))."
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "Creating the Python environment. This takes a minute the first time..."
  if ! "$PY" -m venv .venv 2>/dev/null; then
    echo
    echo "Could not create a virtual environment. On Debian or Ubuntu install it with:"
    echo "    sudo apt install python3-venv"
    exit 1
  fi
  .venv/bin/python -m pip install -q --upgrade pip
  echo "Installing dependencies..."
  if ! .venv/bin/python -m pip install -q -r requirements.txt; then
    echo
    echo "Dependency installation failed. Check your internet connection and try again."
    exit 1
  fi
fi

echo
echo "  Operator — Ferry, Cargo & ACMI"
echo "  Saves are in: $(pwd)/save"
echo "  Close this window or press Ctrl+C to stop."
echo
exec .venv/bin/python server.py "$@"
