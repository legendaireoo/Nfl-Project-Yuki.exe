"""Yuki.exe — Pocket Watch: the Open Lane metric (zero-dependency re-implementation).

A pass rusher has an OPEN LANE on a given frame when:
  * he is within LANE_RANGE yards of the QB, AND
  * no blocker stands within LANE_WIDTH yards of the straight segment joining
    the rusher to the QB (i.e. a clean, unobstructed path to the quarterback).

From the snap-to-throw window we derive, per play:
  * breaks      — did the pocket break (any open lane before the throw)?
  * breachTime  — first time (s after snap) a lane opened
  * breachSide  — which side of the QB it opened on (LEFT / RIGHT / MIDDLE)
  * breachRusher— nflId of the first rusher to get a clean lane

The PFF hit/hurry/sack labels are NOT used in the computation — only, elsewhere,
to validate it. Thresholds are fixed a priori (not tuned).
"""
from __future__ import annotations

import functools
import math
from collections import defaultdict
from typing import Dict, List, Optional

import data_loader as dl

to_float = dl.to_float
to_int = dl.to_int

LANE_WIDTH = 1.0   # yards; max blocker distance to the lane to "block" it
LANE_RANGE = 5.0   # yards; rusher must be this close to the QB
SNAP_EVENTS = {"ball_snap", "autoevent_ballsnap"}
END_EVENTS = {"pass_forward", "autoevent_passforward", "qb_sack",
              "pass_outcome_incomplete", "pass_outcome_caught"}


def _point_segment_dist(px, py, ax, ay, bx, by) -> float:
    """Distance from point P to segment AB."""
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    if seg2 == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / seg2
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def _roles_for_game(game_id: str) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = defaultdict(dict)
    for r in dl.pff():
        if r["gameId"] == game_id:
            out[r["playId"]][r["nflId"]] = r["pff_role"]
    return out


def _play_open_lane(frames_by_id: Dict[int, List[dict]], roles: Dict[str, str]):
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
        return None
    if end is None:
        end = max(frames_by_id)

    def qb_at(fid):
        for r in frames_by_id.get(fid, []):
            if roles.get(r["nflId"]) == "Pass":
                x, y = to_float(r["x"]), to_float(r["y"])
                if x is not None and y is not None:
                    return x, y
        return None

    breach_time = None
    breach_side = None
    breach_rusher = None
    open_frames = 0
    total_frames = 0

    for fid in range(snap, end + 1):
        qb = qb_at(fid)
        if not qb:
            continue
        total_frames += 1
        rushers = []
        blockers = []
        for r in frames_by_id.get(fid, []):
            role = roles.get(r["nflId"])
            x, y = to_float(r["x"]), to_float(r["y"])
            if x is None or y is None:
                continue
            if role == "Pass Rush":
                rushers.append((r["nflId"], x, y))
            elif role == "Pass Block":
                blockers.append((x, y))

        frame_has_lane = False
        for nid, rx, ry in rushers:
            d = math.hypot(rx - qb[0], ry - qb[1])
            if d > LANE_RANGE:
                continue
            blocked = False
            for bx, by in blockers:
                if _point_segment_dist(bx, by, rx, ry, qb[0], qb[1]) < LANE_WIDTH:
                    blocked = True
                    break
            if not blocked:
                frame_has_lane = True
                if breach_time is None:
                    breach_time = round((fid - snap) / 10.0, 1)
                    breach_rusher = nid
                    # side relative to QB along the short axis (y)
                    dy = ry - qb[1]
                    if abs(dy) < 1.5:
                        breach_side = "MIDDLE"
                    else:
                        breach_side = "LEFT" if dy > 0 else "RIGHT"
        if frame_has_lane:
            open_frames += 1

    return {
        "breaks": breach_time is not None,
        "breachTime": breach_time,
        "breachSide": breach_side,
        "breachRusher": breach_rusher,
        "openFrames": open_frames,
        "totalFrames": total_frames,
        "cleanPct": round(100 * (1 - open_frames / total_frames), 1) if total_frames else 0,
    }


@functools.lru_cache(maxsize=8)
def game_lanes(game_id: str) -> Dict[str, dict]:
    rows = dl._tracking_for_game(game_id)
    if not rows:
        return {}
    roles = _roles_for_game(game_id)
    by_play: Dict[str, Dict[int, List[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_play[r["playId"]][to_int(r["frameId"]) or 0].append(r)
    out: Dict[str, dict] = {}
    for pid, frames in by_play.items():
        res = _play_open_lane(frames, roles.get(pid, {}))
        if res is not None:
            out[pid] = res
    return out


def play_lane(game_id: str, play_id: str) -> Optional[dict]:
    return game_lanes(game_id).get(str(play_id))


# ---------------------------------------------------------------------------
# Game pool for the Pocket Watch mini-game + rusher Lane Win Rate leaderboard.
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=4)
def _aggregate(max_games: int) -> dict:
    pbi = dl.players_by_id()
    play_meta: Dict[tuple, dict] = {}
    for p in dl.plays():
        play_meta[(p["gameId"], p["playId"])] = {
            "off": p["possessionTeam"],
            "def": p["defensiveTeam"],
        }
    # official pressure flag per play (for validation only — not in the metric)
    play_pressure: Dict[tuple, bool] = defaultdict(bool)
    rusher_lane: Dict[str, dict] = defaultdict(lambda: {"plays": 0, "wins": 0})
    for r in dl.pff():
        if r["pff_role"] == "Pass Rush":
            key = (r["gameId"], r["playId"])
            if r["pff_hit"] == "1" or r["pff_hurry"] == "1" or r["pff_sack"] == "1":
                play_pressure[key] = True

    games = [g["gameId"] for g in dl.games() if dl.has_tracking(g["gameId"])]
    games = games[:max_games]

    pool: List[dict] = []
    breaks = kept = 0
    broke_and_pressure = kept_and_pressure = 0

    for gid in games:
        lanes = game_lanes(gid)
        for pid, r in lanes.items():
            meta = play_meta.get((gid, pid))
            if not meta:
                continue
            key = (gid, pid)
            if r["breaks"]:
                breaks += 1
                if play_pressure.get(key):
                    broke_and_pressure += 1
                br = r["breachRusher"]
                if br:
                    rusher_lane[br]["plays"] += 1
                    rusher_lane[br]["wins"] += 1
            else:
                kept += 1
                if play_pressure.get(key):
                    kept_and_pressure += 1
            pool.append({
                "gameId": gid, "playId": pid,
                "breaks": r["breaks"], "breachTime": r["breachTime"],
                "breachSide": r["breachSide"], "breachRusher": r["breachRusher"],
                "cleanPct": r["cleanPct"],
                "def": meta["def"], "off": meta["off"],
            })

    # Lane Win Rate leaderboard: how often a rusher is the one who breaks the pocket.
    # Count total rush snaps per player to form a rate.
    snaps: Dict[str, int] = defaultdict(int)
    for r in dl.pff():
        if r["pff_role"] == "Pass Rush" and r["gameId"] in set(games):
            snaps[r["nflId"]] += 1
    leaders = []
    for nid, s in rusher_lane.items():
        total = snaps.get(nid, 0)
        if total < 25:
            continue
        player = pbi.get(nid, {})
        leaders.append({
            "nflId": nid,
            "name": player.get("displayName", f"#{nid}"),
            "position": player.get("officialPosition", ""),
            "snaps": total,
            "laneWins": s["wins"],
            "laneWinRate": round(100 * s["wins"] / total, 1),
        })
    leaders.sort(key=lambda r: r["laneWins"], reverse=True)

    return {
        "gamesAnalyzed": len(games),
        "playsScored": len(pool),
        "breakRate": round(100 * breaks / len(pool), 1) if pool else 0,
        "pressureWhenBreaks": round(100 * broke_and_pressure / breaks, 1) if breaks else 0,
        "pressureWhenClean": round(100 * kept_and_pressure / kept, 1) if kept else 0,
        "leaders": leaders[:30],
        "pool": _balanced_pool(pool),
    }


def _balanced_pool(pool: List[dict], n: int = 60) -> List[dict]:
    """A mix of plays where the pocket breaks and where it holds, for the game."""
    broke = [p for p in pool if p["breaks"]]
    held = [p for p in pool if not p["breaks"]]
    out = []
    i = j = 0
    while len(out) < n and (i < len(broke) or j < len(held)):
        if i < len(broke):
            out.append(broke[i]); i += 1
        if j < len(held) and len(out) < n:
            out.append(held[j]); j += 1
    return out


def summary(max_games: int = 20) -> dict:
    return _aggregate(max_games)
