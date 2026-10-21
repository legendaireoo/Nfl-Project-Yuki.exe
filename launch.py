#!/usr/bin/env python3
"""Yuki.exe — one-click launcher.

Does everything automatically:
  1. Locates the NFL Big Data Bowl dataset (or clones it with git if missing).
  2. Picks a free TCP port.
  3. Starts the Yuki analytics web server.
  4. Opens the dashboard in the default web browser.

Zero third-party dependencies — standard library only. This is the entry point
that gets frozen into Yuki.exe (Windows) / Yuki (macOS, Linux) by build_exe.py,
and the one the Start-Yuki scripts call.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser

# ---------------------------------------------------------------------------
# Resolve our own directory, whether running as a .py or a frozen PyInstaller
# bundle. When frozen, data files are unpacked next to the executable.
# ---------------------------------------------------------------------------
def app_dir() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller onefile: resources live in sys._MEIPASS; the executable
        # itself sits in os.path.dirname(sys.executable).
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def exe_dir() -> str:
    """Directory the user launched the program from (for locating data)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = app_dir()
EXE_DIR = exe_dir()

DATA_REPO_URL = "https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data.git"
DATA_REPO_DIR_NAME = "nfl-big-data-bowl-regional-event-data"


def log(msg: str) -> None:
    print(f"[Yuki] {msg}", flush=True)


# ---------------------------------------------------------------------------
# 1. Locate (or fetch) the dataset
# ---------------------------------------------------------------------------
def candidate_data_dirs():
    """Yield plausible locations for the dataset's 'data' folder."""
    env = os.environ.get("YUKI_DATA_DIR")
    if env:
        yield env
    # next to the executable / project
    for base in (EXE_DIR, os.path.dirname(EXE_DIR), APP_DIR, os.getcwd()):
        yield os.path.join(base, DATA_REPO_DIR_NAME, "data")
        yield os.path.join(base, "data")


def find_data_dir():
    for d in candidate_data_dirs():
        if d and os.path.isfile(os.path.join(d, "games.csv")):
            return os.path.abspath(d)
    return None


def git_available() -> bool:
    try:
        subprocess.run(
            ["git", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False


def clone_dataset():
    """Clone the dataset next to the executable. Returns the data dir or None."""
    target_parent = EXE_DIR
    target = os.path.join(target_parent, DATA_REPO_DIR_NAME)
    data_dir = os.path.join(target, "data")

    if os.path.isdir(target) and os.path.isfile(os.path.join(data_dir, "games.csv")):
        return data_dir

    if not git_available():
        log("ERROR: dataset not found and 'git' is not installed.")
        log("Install git, or download the dataset manually from:")
        log(f"  {DATA_REPO_URL}")
        log(f"...and place its 'data' folder at: {data_dir}")
        return None

    log("Dataset not found — cloning it now (this is a one-time ~800 MB download)...")
    try:
        subprocess.run(["git", "clone", "--depth", "1", DATA_REPO_URL, target], check=True)
    except subprocess.CalledProcessError:
        log("ERROR: git clone failed. Check your internet connection and try again.")
        return None

    if os.path.isfile(os.path.join(data_dir, "games.csv")):
        log("Dataset downloaded successfully.")
        return data_dir
    log("ERROR: dataset clone finished but data files are missing.")
    return None


# ---------------------------------------------------------------------------
# 2. Free port
# ---------------------------------------------------------------------------
def find_free_port(preferred: int = 8000) -> int:
    for port in [preferred] + list(range(8001, 8051)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    # last resort: let the OS pick
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# 3 + 4. Run server and open browser
# ---------------------------------------------------------------------------
def open_browser_when_ready(url: str, host: str, port: int) -> None:
    for _ in range(100):  # up to ~10s
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex((host, port)) == 0:
                break
        time.sleep(0.1)
    log(f"Opening {url} in your browser...")
    try:
        webbrowser.open(url)
    except Exception:
        log(f"Could not open the browser automatically. Go to: {url}")


def main() -> int:
    print("=" * 56)
    print("  Yuki.exe — NFL Big Data Bowl Analytics")
    print("=" * 56)

    # Make sure our modules are importable (config/server/etc.).
    if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)

    # Locate data, cloning if necessary.
    data_dir = find_data_dir()
    if not data_dir:
        data_dir = clone_dataset()
    if not data_dir:
        input("\nPress Enter to exit...")
        return 1
    os.environ["YUKI_DATA_DIR"] = data_dir
    log(f"Using dataset: {data_dir}")

    # Pick a port and expose it to config/server via env.
    port = find_free_port(int(os.environ.get("YUKI_PORT", "8000")))
    host = os.environ.get("YUKI_HOST", "127.0.0.1")
    os.environ["YUKI_PORT"] = str(port)
    os.environ["YUKI_HOST"] = host
    url = f"http://{host}:{port}"

    # Import the server only now that env vars are set.
    import importlib

    import config  # noqa: E402

    importlib.reload(config)  # pick up YUKI_* env overrides
    import server  # noqa: E402

    importlib.reload(server)

    # Open browser in the background once the port is listening.
    threading.Thread(
        target=open_browser_when_ready, args=(url, host, port), daemon=True
    ).start()

    log(f"Starting server at {url}")
    log("Close this window (or press Ctrl+C) to stop Yuki.")
    try:
        server.main()
    except KeyboardInterrupt:
        pass
    log("Yuki stopped. Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
