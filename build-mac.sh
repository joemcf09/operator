#!/usr/bin/env bash
# Operator — build a macOS application and disk image.
#
#   ./build-mac.sh
#
# Produces:
#   dist/Operator.app                  the application
#   dist/Operator-1.0.0-macOS.dmg      drag-to-Applications installer
set -e
cd "$(dirname "$0")"
VER=1.8.0
APP="dist/Operator.app"
DMG="dist/Operator-$VER-macOS.dmg"

echo
echo "  ============================================================"
echo "   Operator — macOS build"
echo "  ============================================================"
echo

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "  Python 3.10 or newer is required."
  echo "  Install it from https://www.python.org/downloads/macos/ and run this again."
  exit 1
fi
if ! "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
  echo "  Python 3.10 or newer is required (found $("$PY" -V))."
  exit 1
fi
echo "  [1/4] Using $("$PY" -V) on $(uname -m)"

if [ ! -x .venv/bin/python ]; then
  echo "  [2/4] Creating the Python environment..."
  "$PY" -m venv .venv
  .venv/bin/python -m pip install -q --upgrade pip
  .venv/bin/python -m pip install -q -r requirements.txt
else
  echo "  [2/4] Python environment found."
fi
.venv/bin/python -m pip install -q --upgrade pyinstaller

echo "  [3/4] Building Operator.app (a couple of minutes)..."
rm -rf build dist
.venv/bin/pyinstaller --noconfirm --log-level WARN operator.spec
if [ ! -d "$APP" ]; then
  echo "  Build failed — see the messages above."
  exit 1
fi

echo "  [4/4] Building the disk image..."
STAGE="$(mktemp -d)"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp docs/README.txt docs/FIRST-RUN.txt docs/MAC-AND-LINUX.txt LICENSE.txt "$STAGE/" 2>/dev/null || true
hdiutil create -volname "Operator $VER" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"

# Gatekeeper will quarantine an unsigned app downloaded from the internet.
shasum -a 256 "$DMG" | awk '{print $1"  '"$(basename "$DMG")"'"}' > dist/SHA256SUMS-macOS.txt

echo
echo "  ============================================================"
echo "   Done."
echo "     Application : $APP"
echo "     Disk image  : $DMG"
echo "     Checksum    : dist/SHA256SUMS-macOS.txt"
echo
echo "   Built for $(uname -m). An Apple Silicon build will not run on"
echo "   an Intel Mac, or the other way round — say which in your listing."
echo "  ============================================================"
echo
open dist 2>/dev/null || true
