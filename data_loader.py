"""Yuki.exe — data access layer.

Loads the NFL Big Data Bowl CSV files using ONLY the Python standard library
(no pandas, so it works in a locked-down sandbox). Core tables are small enough
to keep in memory; tracking files are large and read on demand per game.
"""
from __future__ import annotations

import csv
import functools
import os
from typing import Dict, Iterator, List, Optional

import config

# Raise the field size limit — some play descriptions are long.
csv.field_size_limit(10_000_000)


def _to_float(value: str) -> Optional[float]:
    if value in ("", "NA", "NaN", "None", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: str) -> Optional[int]:
    f = _to_float(value)
    return int(f) if f is not None else None


def _read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# Cached core tables
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def games() -> List[Dict[str, str]]:
    return _read_csv(config.GAMES_CSV)


@functools.lru_cache(maxsize=1)
def players() -> List[Dict[str, str]]:
    return _read_csv(config.PLAYERS_CSV)


@functools.lru_cache(maxsize=1)
def plays() -> List[Dict[str, str]]:
    return _read_csv(config.PLAYS_CSV)


@functools.lru_cache(maxsize=1)
def pff() -> List[Dict[str, str]]:
    return _read_csv(config.PFF_CSV)


@functools.lru_cache(maxsize=1)
def players_by_id() -> Dict[str, Dict[str, str]]:
    return {p["nflId"]: p for p in players()}


@functools.lru_cache(maxsize=1)
def games_by_id() -> Dict[str, Dict[str, str]]:
    return {g["gameId"]: g for g in games()}


@functools.lru_cache(maxsize=1)
def game_week() -> Dict[str, int]:
    out: Dict[str, int] = {}
    for g in games():
        wk = _to_int(g.get("week", ""))
        if wk is not None:
            out[g["gameId"]] = wk
    return out


# ---------------------------------------------------------------------------
# Tracking data (read per game, cached for the few most recently used games)
# ---------------------------------------------------------------------------
def tracking_path(game_id: str) -> str:
    return os.path.join(config.TRACKING_DIR, f"tracking_{game_id}.csv")


def has_tracking(game_id: str) -> bool:
    return os.path.exists(tracking_path(game_id))


@functools.lru_cache(maxsize=4)
def _tracking_for_game(game_id: str) -> List[Dict[str, str]]:
    path = tracking_path(game_id)
    if not os.path.exists(path):
        return []
    return _read_csv(path)


def tracking_play(game_id: str, play_id: str) -> List[Dict[str, str]]:
    """Return all tracking rows for a single play, sorted by frame then player."""
    rows = [r for r in _tracking_for_game(game_id) if r["playId"] == str(play_id)]
    rows.sort(key=lambda r: (_to_int(r["frameId"]) or 0, r.get("nflId", "")))
    return rows


def iter_games() -> Iterator[Dict[str, str]]:
    yield from games()


# Expose helpers to other modules.
to_float = _to_float
to_int = _to_int
