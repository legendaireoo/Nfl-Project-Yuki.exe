"""Yuki.exe — configuration.

Central place for paths and constants. No third-party dependencies.
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Data location
# ---------------------------------------------------------------------------
# By default we look for the NFL Big Data Bowl regional-event dataset that sits
# next to this project in the workspace. Override with the env var YUKI_DATA_DIR.
_DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "nfl-big-data-bowl-regional-event-data",
    "data",
)

DATA_DIR = os.environ.get("YUKI_DATA_DIR", _DEFAULT_DATA_DIR)

GAMES_CSV = os.path.join(DATA_DIR, "games.csv")
PLAYS_CSV = os.path.join(DATA_DIR, "plays.csv")
PLAYERS_CSV = os.path.join(DATA_DIR, "players.csv")
PFF_CSV = os.path.join(DATA_DIR, "pffScoutingData.csv")
TRACKING_DIR = os.path.join(DATA_DIR, "tracking")

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
HOST = os.environ.get("YUKI_HOST", "127.0.0.1")
PORT = int(os.environ.get("YUKI_PORT", "8000"))

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

# Pre-computed datasets shipped with the app (e.g. PROW targeted throws).
WEB_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_data")

# Field dimensions (yards) used by the play viewer.
FIELD_LENGTH = 120.0  # includes both end zones
FIELD_WIDTH = 53.3
