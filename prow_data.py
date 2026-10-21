"""Yuki.exe — PROW ("Fenêtre de tir") data layer.

Reuses the pre-computed Pre-Release Open Window analysis (targeted throws with
separation, open-window duration, missed-window flags and QB ids). The heavy
tracking computation was done once upstream; here we only read the resulting
CSV with the standard library and build interactive aggregates for the UI.

PROW(k) = how long (seconds) the targeted receiver had been continuously at
least k yards from every defender when the ball was released. A "missed window"
is a throw to a covered receiver (< k yd at release) while a teammate had been
open for >= 1 s — a passing chance the box score never shows.
"""
from __future__ import annotations

import csv
import functools
import json
import os
from collections import defaultdict
from typing import Dict, List, Optional

import config
import data_loader as dl

PROW_CSV = os.path.join(config.WEB_DATA_DIR, "prow_targets.csv")
HEADLINE_JSON = os.path.join(config.WEB_DATA_DIR, "prow_headline.json")

THRESHOLDS = [2, 3, 4, 5]
BUCKETS = [
    ("covered", "😶 Couvert au lancer", lambda v: v == 0),
    ("fresh", "⚡ 0.1–0.5 s", lambda v: 0 < v <= 0.5),
    ("short", "🙂 0.6–1.0 s", lambda v: 0.5 < v <= 1.0),
    ("mid", "👍 1.1–2.0 s", lambda v: 1.0 < v <= 2.0),
    ("long", "🕰️ > 2 s", lambda v: v > 2.0),
]


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@functools.lru_cache(maxsize=1)
def rows() -> List[dict]:
    if not os.path.isfile(PROW_CSV):
        return []
    with open(PROW_CSV, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@functools.lru_cache(maxsize=1)
def headline() -> dict:
    if not os.path.isfile(HEADLINE_JSON):
        return {}
    with open(HEADLINE_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def available() -> bool:
    return bool(rows())


@functools.lru_cache(maxsize=8)
def bucket_rates(k: int) -> dict:
    """Completion rate by open-window bucket, for a chosen 'open' threshold k."""
    col = f"prow_{k}"
    agg = {key: {"n": 0, "comp": 0} for key, _, _ in BUCKETS}
    for r in rows():
        v = _f(r.get(col))
        if v is None:
            continue
        comp = r.get("complete") == "1"
        for key, _, test in BUCKETS:
            if test(v):
                agg[key]["n"] += 1
                agg[key]["comp"] += 1 if comp else 0
                break
    out = []
    for key, label, _ in BUCKETS:
        a = agg[key]
        out.append({
            "key": key,
            "label": label,
            "n": a["n"],
            "completionPct": round(100 * a["comp"] / a["n"], 1) if a["n"] else 0,
        })
    # open-vs-covered summary at this threshold
    open_n = sum(a["n"] for a in [x for x in out if x["key"] != "covered"])
    open_c = sum(
        agg[k2]["comp"] for k2 in agg if k2 != "covered"
    )
    cov = out[0]
    return {
        "k": k,
        "buckets": out,
        "openPct": round(100 * open_c / open_n, 1) if open_n else 0,
        "coveredPct": cov["completionPct"],
        "openN": open_n,
        "coveredN": cov["n"],
    }


@functools.lru_cache(maxsize=1)
def qb_missed() -> List[dict]:
    """Per-QB missed-window rate (QBs with >= 150 targeted throws)."""
    pbi = dl.players_by_id()
    agg: Dict[str, dict] = defaultdict(lambda: {"n": 0, "missed": 0})
    for r in rows():
        qid = r.get("qbId", "")
        if not qid or qid in ("", "nan"):
            continue
        qid = qid.split(".")[0]
        a = agg[qid]
        a["n"] += 1
        a["missed"] += 1 if r.get("missed") == "1" else 0
    out = []
    for qid, a in agg.items():
        if a["n"] < 150:
            continue
        player = pbi.get(qid, {})
        out.append({
            "nflId": qid,
            "name": player.get("displayName", f"#{qid}"),
            "throws": a["n"],
            "missedPct": round(100 * a["missed"] / a["n"], 1),
        })
    out.sort(key=lambda r: r["missedPct"], reverse=True)
    return out


@functools.lru_cache(maxsize=4)
def missed_examples(limit: int = 20) -> List[dict]:
    """Clear missed-window plays: covered target, a teammate open a long time."""
    pbi = dl.players_by_id()
    ex = []
    for r in rows():
        if r.get("missed") != "1":
            continue
        alt_prow = _f(r.get("alt_prow_3")) or 0
        sep = _f(r.get("sep_release")) or 0
        if alt_prow < 2 or sep > 1.5:
            continue
        alt_id = (r.get("alt_nflId") or "").split(".")[0]
        ex.append({
            "gameId": r["gameId"],
            "playId": r["playId"],
            "target": r.get("target_abbr", ""),
            "targetSep": round(sep, 1),
            "altName": pbi.get(alt_id, {}).get("displayName", ""),
            "altProw": round(alt_prow, 1),
            "result": r.get("passResult", ""),
            "coverage": r.get("pff_passCoverageType", ""),
        })
    ex.sort(key=lambda r: r["altProw"], reverse=True)
    return ex[:limit]


def summary() -> dict:
    """Everything the interactive PROW tab needs in one payload."""
    h = headline()
    return {
        "available": available(),
        "headline": h,
        "thresholds": THRESHOLDS,
        "qbMissed": qb_missed(),
        "examples": missed_examples(),
        # default view at k=3
        "bucketRates": bucket_rates(3),
    }
