#!/usr/bin/env bash
# ===================================================================
#  Yuki.exe - one-click launcher for macOS / Linux
#  Run with:  ./start-yuki.sh   (or double-click on macOS)
#  Finds Python 3, launches the server, opens your browser.
# ===================================================================
set -e
cd "$(dirname "$0")"

echo "Starting Yuki.exe ..."

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo
    echo "[ERROR] Python 3 was not found."
    echo "        macOS:  brew install python   (or https://www.python.org/downloads/)"
    echo "        Linux:  sudo apt install python3   (or your package manager)"
    echo
    exit 1
fi

exec "$PY" launch.py
