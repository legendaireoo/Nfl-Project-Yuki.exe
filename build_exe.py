#!/usr/bin/env python3
"""Yuki.exe — build a standalone executable with PyInstaller.

Produces a single self-contained binary so end users do NOT need Python:
  * Windows -> dist/Yuki.exe
  * macOS   -> dist/Yuki
  * Linux   -> dist/Yuki

Usage:
    pip install pyinstaller
    python build_exe.py

Notes
-----
* PyInstaller builds for the OS it runs on. Build on Windows to get a .exe,
  on macOS to get a macOS binary, etc.
* The ~800 MB NFL dataset is NOT bundled. On first run the executable clones
  it automatically with git (see launch.py), or you can place the
  'nfl-big-data-bowl-regional-event-data' folder next to the executable.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEP = ";" if os.name == "nt" else ":"  # PyInstaller --add-data separator


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed. Install it with:\n    pip install pyinstaller")
        sys.exit(1)


def build() -> None:
    ensure_pyinstaller()

    # Bundle the frontend assets and all backend modules.
    add_data = [
        f"web{SEP}web",
        f"web_data{SEP}web_data",
        f"config.py{SEP}.",
        f"server.py{SEP}.",
        f"analytics.py{SEP}.",
        f"metrics.py{SEP}.",
        f"prow_data.py{SEP}.",
        f"data_loader.py{SEP}.",
    ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name",
        "Yuki",
        "--clean",
        "--noconfirm",
        # make sure our sibling modules are collected
        "--hidden-import", "config",
        "--hidden-import", "server",
        "--hidden-import", "analytics",
        "--hidden-import", "metrics",
        "--hidden-import", "prow_data",
        "--hidden-import", "data_loader",
    ]
    for spec in add_data:
        cmd += ["--add-data", spec]
    cmd.append("launch.py")

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=HERE, check=True)

    out = os.path.join(HERE, "dist", "Yuki.exe" if os.name == "nt" else "Yuki")
    print("\n" + "=" * 56)
    if os.path.exists(out):
        size = os.path.getsize(out) / (1024 * 1024)
        print(f"  Build complete: {out}  ({size:.1f} MB)")
        print("  Ship this single file. On first launch it will fetch the")
        print("  dataset automatically (needs git + internet, one time).")
    else:
        print("  Build finished but the expected output was not found.")
        print("  Check the PyInstaller output above for errors.")
    print("=" * 56)


if __name__ == "__main__":
    build()
