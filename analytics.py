"""Yuki.exe — analytics engine.

All computations run against the in-memory core tables from data_loader.
Pure standard library. Results are returned as plain dicts/lists so the HTTP
layer can serialize them straight to JSON.
"""
from __future__ import annotations

import functools
from collections import defaultdict
from typing import Dict, List, Optional

import data_loader as dl

to_float = dl.to_float
to_int = dl.to_int


# ---------------------------------------------------------------------------
# Overview / summary
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def overview() -> Dict:
    plays = dl.plays()
    pff = dl.pff()

    n_plays = len(plays)
    results = defaultdict(int)
    coverage = defaultdict(int)
    formation = defaultdict(int)
    yards = []
    play_action = 0
    for p in plays:
        results[p["passResult"] or "NA"] += 1
        coverage[p["pff_passCoverage"] or "NA"] += 1
        formation[p["offenseFormation"] or "NA"] += 1
        pr = to_float(p.get("playResult", ""))
        if pr is not None:
            yards.append(pr)
        if p.get("pff_playAction") == "1":
            play_action += 1

    hits = hurries = sacks = 0
    for r in pff:
        if r["pff_hit"] == "1":
            hits += 1
        if r["pff_hurry"] == "1":
            hurries += 1
        if r["pff_sack"] == "1":
            sacks += 1

    completions = results.get("C", 0)
    attempts = completions + results.get("I", 0) + results.get("IN", 0)

    return {
        "games": len(dl.games()),
        "players": len(dl.players()),
        "plays": n_plays,
        "weeks": sorted(set(dl.game_week().values())),
        "totalPressures": hits + hurries + sacks,
        "hits": hits,
        "hurries": hurries,
        "sacks": sacks,
        "completionPct": round(100 * completions / attempts, 1) if attempts else 0,
        "avgYards": round(sum(yards) / len(yards), 2) if yards else 0,
        "playActionPct": round(100 * play_action / n_plays, 1) if n_plays else 0,
        "passResults": dict(results),
        "coverages": dict(coverage),
        "formations": dict(formation),
    }


# ---------------------------------------------------------------------------
# Coverage analysis — efficiency of each defensive coverage scheme
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def coverage_analysis() -> List[Dict]:
    agg: Dict[str, Dict] = defaultdict(
        lambda: {"plays": 0, "comp": 0, "att": 0, "yards": 0.0, "epaCount": 0}
    )
    for p in dl.plays():
        cov = p["pff_passCoverage"] or "NA"
        a = agg[cov]
        a["plays"] += 1
        res = p["passResult"]
        if res in ("C", "I", "IN"):
            a["att"] += 1
            if res == "C":
                a["comp"] += 1
        pr = to_float(p.get("playResult", ""))
        if pr is not None:
            a["yards"] += pr
            a["epaCount"] += 1

    out = []
    for cov, a in agg.items():
        out.append(
            {
                "coverage": cov,
                "plays": a["plays"],
                "completionPct": round(100 * a["comp"] / a["att"], 1) if a["att"] else 0,
                "avgYards": round(a["yards"] / a["epaCount"], 2) if a["epaCount"] else 0,
            }
        )
    out.sort(key=lambda r: r["plays"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# Pass-rush leaderboard — top disruptors from PFF scouting data
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def pass_rush_leaders(limit: int = 40) -> List[Dict]:
    stats: Dict[str, Dict] = defaultdict(
        lambda: {"snaps": 0, "hits": 0, "hurries": 0, "sacks": 0}
    )
    for r in dl.pff():
        if r["pff_role"] != "Pass Rush":
            continue
        nid = r["nflId"]
        s = stats[nid]
        s["snaps"] += 1
        s["hits"] += 1 if r["pff_hit"] == "1" else 0
        s["hurries"] += 1 if r["pff_hurry"] == "1" else 0
        s["sacks"] += 1 if r["pff_sack"] == "1" else 0

    pbi = dl.players_by_id()
    rows = []
    for nid, s in stats.items():
        pressures = s["hits"] + s["hurries"] + s["sacks"]
        if s["snaps"] < 20:
            continue
        player = pbi.get(nid, {})
        rows.append(
            {
                "nflId": nid,
                "name": player.get("displayName", f"#{nid}"),
                "position": player.get("officialPosition", ""),
                "snaps": s["snaps"],
                "hits": s["hits"],
                "hurries": s["hurries"],
                "sacks": s["sacks"],
                "pressures": pressures,
                "pressureRate": round(100 * pressures / s["snaps"], 1),
            }
        )
    rows.sort(key=lambda r: (r["pressures"], r["pressureRate"]), reverse=True)
    return rows[:limit]


# ---------------------------------------------------------------------------
# Pass-block leaderboard — best protectors (fewest pressures allowed)
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def pass_block_leaders(limit: int = 40) -> List[Dict]:
    stats: Dict[str, Dict] = defaultdict(
        lambda: {"snaps": 0, "hits": 0, "hurries": 0, "sacks": 0}
    )
    for r in dl.pff():
        if r["pff_role"] != "Pass Block":
            continue
        nid = r["nflId"]
        s = stats[nid]
        s["snaps"] += 1
        s["hits"] += 1 if r["pff_hitAllowed"] == "1" else 0
        s["hurries"] += 1 if r["pff_hurryAllowed"] == "1" else 0
        s["sacks"] += 1 if r["pff_sackAllowed"] == "1" else 0

    pbi = dl.players_by_id()
    rows = []
    for nid, s in stats.items():
        if s["snaps"] < 50:
            continue
        allowed = s["hits"] + s["hurries"] + s["sacks"]
        player = pbi.get(nid, {})
        rows.append(
            {
                "nflId": nid,
                "name": player.get("displayName", f"#{nid}"),
                "position": player.get("officialPosition", ""),
                "snaps": s["snaps"],
                "hitsAllowed": s["hits"],
                "hurriesAllowed": s["hurries"],
                "sacksAllowed": s["sacks"],
                "pressuresAllowed": allowed,
                "pressureAllowedRate": round(100 * allowed / s["snaps"], 2),
            }
        )
    # Best protectors first: lowest pressure-allowed rate.
    rows.sort(key=lambda r: (r["pressureAllowedRate"], -r["snaps"]))
    return rows[:limit]


# ---------------------------------------------------------------------------
# Team pass-protection / pass-rush summary
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def team_analysis() -> List[Dict]:
    # Map (gameId, playId) -> (possessionTeam, defensiveTeam)
    play_teams: Dict[tuple, tuple] = {}
    for p in dl.plays():
        play_teams[(p["gameId"], p["playId"])] = (
            p["possessionTeam"],
            p["defensiveTeam"],
        )

    off: Dict[str, Dict] = defaultdict(lambda: {"snaps": 0, "allowed": 0})
    deff: Dict[str, Dict] = defaultdict(lambda: {"snaps": 0, "pressures": 0})

    for r in dl.pff():
        key = (r["gameId"], r["playId"])
        teams = play_teams.get(key)
        if not teams:
            continue
        offense, defense = teams
        if r["pff_role"] == "Pass Block":
            o = off[offense]
            o["snaps"] += 1
            if r["pff_hitAllowed"] == "1" or r["pff_hurryAllowed"] == "1" or r["pff_sackAllowed"] == "1":
                o["allowed"] += 1
        elif r["pff_role"] == "Pass Rush":
            d = deff[defense]
            d["snaps"] += 1
            if r["pff_hit"] == "1" or r["pff_hurry"] == "1" or r["pff_sack"] == "1":
                d["pressures"] += 1

    teams = sorted(set(list(off.keys()) + list(deff.keys())))
    out = []
    for t in teams:
        o = off.get(t, {"snaps": 0, "allowed": 0})
        d = deff.get(t, {"snaps": 0, "pressures": 0})
        out.append(
            {
                "team": t,
                "blockSnaps": o["snaps"],
                "pressuresAllowed": o["allowed"],
                "pressureAllowedRate": round(100 * o["allowed"] / o["snaps"], 1) if o["snaps"] else 0,
                "rushSnaps": d["snaps"],
                "pressuresGenerated": d["pressures"],
                "pressureRate": round(100 * d["pressures"] / d["snaps"], 1) if d["snaps"] else 0,
            }
        )
    out.sort(key=lambda r: r["pressureRate"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# Play index + detail (for the tracking viewer)
# ---------------------------------------------------------------------------
def play_list(game_id: Optional[str] = None, limit: int = 300) -> List[Dict]:
    gbi = dl.games_by_id()
    rows = []
    for p in dl.plays():
        if game_id and p["gameId"] != game_id:
            continue
        if not dl.has_tracking(p["gameId"]):
            continue
        g = gbi.get(p["gameId"], {})
        rows.append(
            {
                "gameId": p["gameId"],
                "playId": p["playId"],
                "week": dl.game_week().get(p["gameId"]),
                "home": g.get("homeTeamAbbr", ""),
                "visitor": g.get("visitorTeamAbbr", ""),
                "possessionTeam": p["possessionTeam"],
                "quarter": p["quarter"],
                "down": p["down"],
                "yardsToGo": p["yardsToGo"],
                "coverage": p["pff_passCoverage"],
                "passResult": p["passResult"],
                "description": p["playDescription"],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def game_list() -> List[Dict]:
    gbi = dl.games_by_id()
    out = []
    for g in dl.games():
        if not dl.has_tracking(g["gameId"]):
            continue
        out.append(
            {
                "gameId": g["gameId"],
                "week": to_int(g.get("week", "")),
                "label": f"Week {g.get('week')}: {g.get('visitorTeamAbbr')} @ {g.get('homeTeamAbbr')}",
                "home": g.get("homeTeamAbbr"),
                "visitor": g.get("visitorTeamAbbr"),
            }
        )
    out.sort(key=lambda r: (r["week"] or 0, r["gameId"]))
    return out


def play_detail(game_id: str, play_id: str) -> Dict:
    """Return play metadata plus frame-by-frame tracking for the viewer."""
    meta = None
    for p in dl.plays():
        if p["gameId"] == game_id and p["playId"] == str(play_id):
            meta = p
            break

    rows = dl.tracking_play(game_id, play_id)
    pbi = dl.players_by_id()

    frames: Dict[int, List[Dict]] = defaultdict(list)
    direction = "right"
    for r in rows:
        fid = to_int(r["frameId"]) or 0
        direction = r.get("playDirection", direction)
        nid = r.get("nflId", "")
        player = pbi.get(nid, {}) if nid not in ("", "NA") else {}
        frames[fid].append(
            {
                "nflId": nid if nid not in ("", "NA") else None,
                "team": r.get("team", ""),
                "jersey": r.get("jerseyNumber", ""),
                "name": player.get("displayName", ""),
                "position": player.get("officialPosition", ""),
                "x": to_float(r["x"]),
                "y": to_float(r["y"]),
                "s": to_float(r["s"]),
                "o": to_float(r["o"]),
                "dir": to_float(r["dir"]),
                "event": r.get("event") if r.get("event") not in ("None", "") else None,
            }
        )

    ordered = [frames[f] for f in sorted(frames.keys())]

    home = ""
    visitor = ""
    g = dl.games_by_id().get(game_id, {})
    home = g.get("homeTeamAbbr", "")
    visitor = g.get("visitorTeamAbbr", "")

    # Attach the per-frame PPI timeline so the viewer can show a live pressure
    # meter and spotlight the top rusher. Imported lazily to avoid a cycle.
    ppi_series = None
    try:
        import metrics

        ppi_series = metrics.play_ppi_series(game_id, play_id)
    except Exception:
        ppi_series = None

    return {
        "gameId": game_id,
        "playId": play_id,
        "home": home,
        "visitor": visitor,
        "playDirection": direction,
        "ppi": ppi_series,
        "meta": {
            "description": meta.get("playDescription") if meta else "",
            "quarter": meta.get("quarter") if meta else "",
            "down": meta.get("down") if meta else "",
            "yardsToGo": meta.get("yardsToGo") if meta else "",
            "possessionTeam": meta.get("possessionTeam") if meta else "",
            "defensiveTeam": meta.get("defensiveTeam") if meta else "",
            "coverage": meta.get("pff_passCoverage") if meta else "",
            "passResult": meta.get("passResult") if meta else "",
            "absoluteYardlineNumber": to_float(meta.get("absoluteYardlineNumber", "")) if meta else None,
        }
        if meta
        else {},
        "frameCount": len(ordered),
        "frames": ordered,
    }


# ---------------------------------------------------------------------------
# Player search + profile
# ---------------------------------------------------------------------------
def player_search(query: str, limit: int = 20) -> List[Dict]:
    q = query.lower().strip()
    out = []
    for p in dl.players():
        if q in p["displayName"].lower():
            out.append(
                {
                    "nflId": p["nflId"],
                    "name": p["displayName"],
                    "position": p["officialPosition"],
                    "college": p["collegeName"],
                }
            )
        if len(out) >= limit:
            break
    return out
