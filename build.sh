#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Run ./run.sh once first to create the environment."; exit 1; }
.venv/bin/python -m pip install -q --upgrade pyinstaller
rm -rf build dist
.venv/bin/pyinstaller --noconfirm operator.spec
echo "Built dist/Operator/Operator"
echo "(The Windows installer is produced by build.bat with Inno Setup 6 installed.)"
