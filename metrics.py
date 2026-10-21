"""Yuki.exe — PPI: the Pocket Pressure Index (an original tracking-derived metric).

WHAT IT IS
----------
PFF's data only tells you *whether* a QB was hit / hurried / sacked — a binary
flag. PPI instead measures *how much heat the quarterback actually felt* on a
play, as a continuous 0–100 score computed purely from the frame-by-frame
tracking geometry between the snap and the throw.

For every tracking frame in the dropback window we look at each pass rusher and
score the threat they pose to the QB from three physical ingredients:

  1. PROXIMITY   — how close the rusher is (weighted exponentially: a defender
                   2 yards away is far scarier than one 6 yards away).
  2. CLOSING     — the component of the rusher's velocity vector pointing
                   straight at the QB (a rusher sprinting *at* the QB is a real
                   threat; one running past him is not).
  3. URGENCY     — how fast the whole pocket broke down (time-to-throw): quick
                   breakdowns are penalised.

The peak single-frame pressure drives the play's PPI, and each rusher's share
of that pressure is credited back to them — so we also get, for free:

  * PPI GENERATED  — a continuous pass-rush productivity score per defender,
                     richer than counting binary hurries.
  * PPI ALLOWED    — pocket pressure yielded, chargeable to the offense.
  * GHOST PRESSURE — PPI a rusher generated on plays where PFF logged NO
                     official hit/hurry/sack: pressure the box score misses.

Everything here is standard-library only.
"""
from __future__ import annotations

import functools
import math
from collections import defaultdict
from typing import Dict, List, Optional

import data_loader as dl

to_float = dl.to_float
to_int = dl.to_int

SNAP_EVENTS = {"ball_snap", "autoevent_ballsnap"}
END_EVENTS = {"pass_forward", "autoevent_passforward", "qb_sack",
              "pass_outcome_incomplete", "pass_outcome_caught"}

# Tuning constants (documented so the metric is reproducible / inspectable).
PROX_DECAY = 2.5       # yards; smaller => proximity matters more sharply
CLOSING_WEIGHT = 0.6   # how much converging speed amplifies a threat
MAX_RANGE = 10.0       # yards; rushers farther than this are ignored
URGENCY_REF = 3.0      # seconds; throws faster than this add urgency pressure
URGENCY_WEIGHT = 0.3
SCALE = 18.0           # maps raw pressure onto a readable 0–100 band


def _roles_for_game(game_id: str) -> Dict[str, Dict[str, str]]:
    """playId -> {nflId: pff_role} for one game."""
    out: Dict[str, Dict[str, str]] = defaultdict(dict)
    for r in dl.pff():
        if r["gameId"] == game_id:
            out[r["playId"]][r["nflId"]] = r["pff_role"]
    return out


def _play_ppi(frames_by_id: Dict[int, List[dict]], roles: Dict[str, str]):
    """Compute PPI for a single play. Returns dict or None if not a dropback."""
    if not frames_by_id:
        return None

    snap = end = None
    for fid in sorted(frames_by_id):
        for r in frames_by_id[fid]:
            ev = r.get("event")
            if ev in SNAP_EVENTS and snap is None:
                snap = fid
            if ev in END_EVENTS and end is None and (snap is not None):
                end = fid
    if snap is None:
        return None
    if end is None:
        end = max(frames_by_id)  # sack / scramble: use the whole window

    def qb_at(fid: int):
        for r in frames_by_id.get(fid, []):
            if roles.get(r["nflId"]) == "Pass":
                x, y = to_float(r["x"]), to_float(r["y"])
                if x is not None and y is not None:
                    return x, y
        return None

    peak = 0.0
    peak_frame = snap
    contrib: Dict[str, float] = defaultdict(float)

    for fid in range(snap, end + 1):
        qb = qb_at(fid)
        if not qb:
            continue
        frame_pressure = 0.0
        for r in frames_by_id.get(fid, []):
            if roles.get(r["nflId"]) != "Pass Rush":
                continue
            rx, ry = to_float(r["x"]), to_float(r["y"])
            if rx is None or ry is None:
                continue
            d = math.hypot(rx - qb[0], ry - qb[1])
            if d > MAX_RANGE:
                continue
            s = to_float(r["s"]) or 0.0
            dirdeg = to_float(r["dir"])
            closing = 0.0
            if dirdeg is not None:
                vx = math.sin(math.radians(dirdeg)) * s
                vy = math.cos(math.radians(dirdeg)) * s
                tox, toy = qb[0] - rx, qb[1] - ry
                tl = math.hypot(tox, toy) or 1.0
                closing = max(0.0, (vx * tox + vy * toy) / tl)
            prox = math.exp(-d / PROX_DECAY)
            p = prox * (1 + closing * CLOSING_WEIGHT)
            frame_pressure += p
            contrib[r["nflId"]] += p
        if frame_pressure > peak:
            peak = frame_pressure
            peak_frame = fid

    ttt = (end - snap) / 10.0
    urgency = 1 + max(0.0, (URGENCY_REF - ttt)) * URGENCY_WEIGHT
    ppi = round(min(100.0, peak * urgency * SCALE), 1)

    # distribute play PPI to rushers by their share of accumulated pressure
    total = sum(contrib.values()) or 1.0
    rusher_ppi = {nid: round(ppi * (v / total), 1) for nid, v in contrib.items()}

    return {
        "ppi": ppi,
        "timeToThrow": round(ttt, 2),
        "snapFrame": snap,
        "endFrame": end,
        "peakFrame": peak_frame,
        "rusherPPI": rusher_ppi,
    }


@functools.lru_cache(maxsize=8)
def game_ppi(game_id: str) -> Dict[str, dict]:
    """playId -> PPI result for every dropback in a game (cached)."""
    rows = dl._tracking_for_game(game_id)
    if not rows:
        return {}
    roles = _roles_for_game(game_id)
    by_play: Dict[str, Dict[int, List[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_play[r["playId"]][to_int(r["frameId"]) or 0].append(r)

    out: Dict[str, dict] = {}
    for pid, frames in by_play.items():
        res = _play_ppi(frames, roles.get(pid, {}))
        if res is not None:
            out[pid] = res
    return out


def play_ppi(game_id: str, play_id: str) -> Optional[dict]:
    return game_ppi(game_id).get(str(play_id))


def play_ppi_series(game_id: str, play_id: str) -> Optional[dict]:
    """Per-frame PPI timeline for the live pressure meter in the Play Viewer.

    Returns, for each frame in the dropback window, the total pressure on the
    QB and the single most threatening rusher's nflId — so the UI can draw a
    rising pressure gauge and spotlight the key defender in real time.
    """
    rows = dl._tracking_for_game(game_id)
    if not rows:
        return None
    roles = _roles_for_game(game_id).get(str(play_id), {})
    frames_by_id: Dict[int, List[dict]] = defaultdict(list)
    for r in rows:
        if r["playId"] == str(play_id):
            frames_by_id[to_int(r["frameId"]) or 0].append(r)
    if not frames_by_id:
        return None

    snap = end = None
    for fid in sorted(frames_by_id):
        for r in frames_by_id[fid]:
            ev = r.get("event")
            if ev in SNAP_EVENTS and snap is None:
                snap = fid
            if ev in END_EVENTS and end is None and snap is not None:
                end = fid
    if snap is None:
        snap = min(frames_by_id)
    if end is None:
        end = max(frames_by_id)

    def qb_at(fid):
        for r in frames_by_id.get(fid, []):
            if roles.get(r["nflId"]) == "Pass":
                x, y = to_float(r["x"]), to_float(r["y"])
                if x is not None and y is not None:
                    return x, y
        return None

    series = []  # one entry per frame index (aligned to the viewer's frames)
    all_frames = sorted(frames_by_id)
    peak = 0.0
    for fid in all_frames:
        if fid < snap or fid > end:
            series.append({"pressure": 0.0, "topRusher": None, "active": False})
            continue
        qb = qb_at(fid)
        if not qb:
            series.append({"pressure": 0.0, "topRusher": None, "active": True})
            continue
        frame_pressure = 0.0
        best_nid = None
        best_p = 0.0
        for r in frames_by_id.get(fid, []):
            if roles.get(r["nflId"]) != "Pass Rush":
                continue
            rx, ry = to_float(r["x"]), to_float(r["y"])
            if rx is None or ry is None:
                continue
            d = math.hypot(rx - qb[0], ry - qb[1])
            if d > MAX_RANGE:
                continue
            s = to_float(r["s"]) or 0.0
            dirdeg = to_float(r["dir"])
            closing = 0.0
            if dirdeg is not None:
                vx = math.sin(math.radians(dirdeg)) * s
                vy = math.cos(math.radians(dirdeg)) * s
                tox, toy = qb[0] - rx, qb[1] - ry
                tl = math.hypot(tox, toy) or 1.0
                closing = max(0.0, (vx * tox + vy * toy) / tl)
            p = math.exp(-d / PROX_DECAY) * (1 + closing * CLOSING_WEIGHT)
            frame_pressure += p
            if p > best_p:
                best_p, best_nid = p, r["nflId"]
        peak = max(peak, frame_pressure)
        series.append(
            {"pressure": round(frame_pressure, 3), "topRusher": best_nid, "active": True}
        )

    # normalise each frame to 0-100 against this play's peak for a clean gauge
    scale = (1.0 / peak) if peak > 0 else 0.0
    for s in series:
        s["gauge"] = round(min(100.0, s["pressure"] * scale * 100), 1)

    summary = game_ppi(game_id).get(str(play_id), {})
    return {
        "snapFrame": snap,
        "endFrame": end,
        "playPPI": summary.get("ppi"),
        "timeToThrow": summary.get("timeToThrow"),
        "series": series,
    }


# ---------------------------------------------------------------------------
# League-wide aggregates. Computing PPI for all 122 games means reading every
# tracking file, so this is cached and can be limited to the first N games.
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=4)
def _aggregate(max_games: int) -> dict:
    pbi = dl.players_by_id()
    # play -> teams + official pressure flags
    play_meta: Dict[tuple, dict] = {}
    for p in dl.plays():
        play_meta[(p["gameId"], p["playId"])] = {
            "off": p["possessionTeam"],
            "def": p["defensiveTeam"],
        }
    # official pressure (any) per (game,play,nflId) for ghost-pressure calc
    official: Dict[tuple, bool] = {}
    for r in dl.pff():
        if r["pff_role"] == "Pass Rush":
            flag = r["pff_hit"] == "1" or r["pff_hurry"] == "1" or r["pff_sack"] == "1"
            official[(r["gameId"], r["playId"], r["nflId"])] = flag

    rusher: Dict[str, dict] = defaultdict(
        lambda: {"plays": 0, "ppi": 0.0, "ghost": 0.0, "ghostPlays": 0}
    )
    team_def: Dict[str, dict] = defaultdict(lambda: {"plays": 0, "ppi": 0.0})
    team_off: Dict[str, dict] = defaultdict(lambda: {"plays": 0, "ppi": 0.0})
    play_scores: List[dict] = []

    games = [g["gameId"] for g in dl.games() if dl.has_tracking(g["gameId"])]
    games = games[:max_games]

    for gid in games:
        res = game_ppi(gid)
        for pid, r in res.items():
            meta = play_meta.get((gid, pid))
            if not meta:
                continue
            team_def[meta["def"]]["plays"] += 1
            team_def[meta["def"]]["ppi"] += r["ppi"]
            team_off[meta["off"]]["plays"] += 1
            team_off[meta["off"]]["ppi"] += r["ppi"]
            play_scores.append(
                {"gameId": gid, "playId": pid, "ppi": r["ppi"],
                 "timeToThrow": r["timeToThrow"], "def": meta["def"], "off": meta["off"]}
            )
            for nid, val in r["rusherPPI"].items():
                st = rusher[nid]
                st["plays"] += 1
                st["ppi"] += val
                if not official.get((gid, pid, nid), False):
                    st["ghost"] += val
                    st["ghostPlays"] += 1

    def finalize_players(d):
        rows = []
        for nid, s in d.items():
            if s["plays"] < 15:
                continue
            player = pbi.get(nid, {})
            rows.append({
                "nflId": nid,
                "name": player.get("displayName", f"#{nid}"),
                "position": player.get("officialPosition", ""),
                "plays": s["plays"],
                "totalPPI": round(s["ppi"], 1),
                "ppiPerPlay": round(s["ppi"] / s["plays"], 2),
                "ghostPPI": round(s["ghost"], 1),
                "ghostPlays": s["ghostPlays"],
            })
        return rows

    rushers = finalize_players(rusher)
    rushers.sort(key=lambda r: r["totalPPI"], reverse=True)

    def team_rows(d):
        rows = []
        for t, s in d.items():
            if not s["plays"]:
                continue
            rows.append({"team": t, "plays": s["plays"],
                         "avgPPI": round(s["ppi"] / s["plays"], 1)})
        return rows

    teams_def = sorted(team_rows(team_def), key=lambda r: r["avgPPI"], reverse=True)
    teams_off = sorted(team_rows(team_off), key=lambda r: r["avgPPI"])

    play_scores.sort(key=lambda r: r["ppi"], reverse=True)

    # Keep a spread of plays across the whole pressure range for the mini-game:
    # sample evenly through the sorted list so every level (calm..infernal) shows up.
    spread = []
    if play_scores:
        step = max(1, len(play_scores) // 60)
        spread = play_scores[::step][:60]

    return {
        "gamesAnalyzed": len(games),
        "playsScored": len(play_scores),
        "avgPPI": round(sum(p["ppi"] for p in play_scores) / len(play_scores), 1)
        if play_scores else 0,
        "rushers": rushers[:50],
        "ghostLeaders": sorted(rushers, key=lambda r: r["ghostPPI"], reverse=True)[:25],
        "teamsDefense": teams_def,
        "teamsOffense": teams_off,
        "topPlays": play_scores[:25],
        "quizPlays": spread,
    }


def leaderboard(max_games: int = 20) -> dict:
    """PPI leaderboards. Defaults to the first 20 games for responsiveness."""
    return _aggregate(max_games)


@functools.lru_cache(maxsize=4)
def game_pool(max_games: int = 6) -> dict:
    """Lightweight: just a spread of scored plays for the mini-game.

    Skips the rusher/ghost/team aggregation so the game starts fast.
    """
    play_scores: List[dict] = []
    games = [g["gameId"] for g in dl.games() if dl.has_tracking(g["gameId"])]
    games = games[:max_games]
    for gid in games:
        res = game_ppi(gid)
        for pid, r in res.items():
            play_scores.append({
                "gameId": gid, "playId": pid, "ppi": r["ppi"],
                "timeToThrow": r["timeToThrow"],
            })
    play_scores.sort(key=lambda r: r["ppi"], reverse=True)
    spread = []
    if play_scores:
        step = max(1, len(play_scores) // 60)
        spread = play_scores[::step][:60]
    return {"quizPlays": spread, "gamesAnalyzed": len(games), "playsScored": len(play_scores)}
