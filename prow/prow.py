"""OPEN BUT UNREACHABLE? -- Pre-Release Open Window (PROW).

PROW(k) for a route runner = how long (seconds) he has been continuously >= k yards
from the nearest defender, counted backwards from the pass_forward frame.
If he is not >= k yards from everyone at release, PROW(k) = 0.

Only tracking frames between ball_snap and pass_forward are used to compute the metric.
The pass outcome (plays.csv passResult) and the targeted receiver (parsed from the
official play-by-play text) are used ONLY to evaluate the metric, never inside it.

Usage:
    python download_data.py      # once (~810 MB)
    python prow.py               # features (cached) + stats + figures -> ./output
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- configuration
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
TRACK_DIR = DATA_DIR / "tracking"
OUT_DIR = ROOT / "output"
FEATURES_CSV = OUT_DIR / "receiver_features.csv"

THRESHOLDS = [2.0, 3.0, 4.0, 5.0]  # yards, sensitivity grid
PRIMARY_K = 3.0                     # yards, headline threshold
SNAP_EVENTS = ["ball_snap", "autoevent_ballsnap"]
RELEASE_EVENTS = ["pass_forward", "autoevent_passforward"]
PASS_RESULTS = ["C", "I", "IN"]     # plays with an actual forward pass

# "QB pass [incomplete] short|deep left|right|middle F.Last ..."
TARGET_RE = re.compile(
    r"pass (?:incomplete )?(?:short |deep )?(?:left |right |middle )?(?:to |intended for )"
    r"([A-Z][A-Za-z']*\.\s?[A-Z][A-Za-z'\-]*(?:\.[A-Z][A-Za-z'\-]*)?)"
)


# ---------------------------------------------------------------- loading
def require(path: Path) -> Path:
    if not path.exists():
        sys.exit(f"Missing {path}. Run `python download_data.py` first.")
    return path


def load_meta():
    plays = pd.read_csv(require(DATA_DIR / "plays.csv"))
    scout = pd.read_csv(require(DATA_DIR / "pffScoutingData.csv"),
                        usecols=["gameId", "playId", "nflId", "pff_role", "pff_positionLinedUp"])
    players = pd.read_csv(require(DATA_DIR / "players.csv"),
                          usecols=["nflId", "displayName", "officialPosition"])
    games = pd.read_csv(require(DATA_DIR / "games.csv"))
    assert not plays.duplicated(["gameId", "playId"]).any()
    assert not scout.duplicated(["gameId", "playId", "nflId"]).any()
    assert not players.duplicated("nflId").any()
    return plays, scout, players, games


def abbrev(name: str) -> str:
    """'Cooper Kupp' -> 'C.Kupp' (play-by-play style)."""
    parts = str(name).split()
    return f"{parts[0][0]}.{parts[-1]}" if len(parts) >= 2 else str(name)


def parse_target(desc: str):
    m = TARGET_RE.search(str(desc))
    return m.group(1).replace(" ", "") if m else None


# ---------------------------------------------------------------- metric
def open_window(sep: np.ndarray, k: float, fps: float) -> float:
    """Seconds of consecutive frames with sep >= k ending at the last (release) frame."""
    above = sep >= k
    if not above[-1]:
        return 0.0
    closed = np.flatnonzero(~above)
    n = len(above) - (closed[-1] + 1 if len(closed) else 0)
    return n / fps


def play_separation(trk: pd.DataFrame, offense: str, receivers: list):
    """Nearest-defender distance per receiver per frame, snap..release.

    Returns (frames, {nflId: sep array}, positions DataFrame) or None if events are missing.
    """
    ball = trk[trk.team == "football"]
    ev = ball.dropna(subset=["event"]).set_index("event").frameId
    snap = ev[ev.index.isin(SNAP_EVENTS)].min()
    rel = ev[ev.index.isin(RELEASE_EVENTS)].min()
    if pd.isna(snap) or pd.isna(rel) or rel <= snap:
        return None
    w = trk[(trk.frameId >= snap) & (trk.frameId <= rel)]
    pos = w.pivot_table(index="frameId", columns="nflId", values=["x", "y"])
    frames = pos.index.values
    def_ids = w.loc[(w.team != offense) & (w.team != "football"), "nflId"].unique()
    dx, dy = pos["x"][def_ids].values, pos["y"][def_ids].values  # F x D
    seps = {}
    for r in receivers:
        if r not in pos["x"].columns:
            continue
        rx, ry = pos["x"][r].values[:, None], pos["y"][r].values[:, None]
        seps[r] = np.nanmin(np.hypot(dx - rx, dy - ry), axis=1)
    return frames, seps, (snap, rel)


def standardize(trk: pd.DataFrame) -> pd.DataFrame:
    """Offense always moves toward +x."""
    trk = trk.copy()
    left = trk.playDirection == "left"
    trk.loc[left, "x"] = 120 - trk.loc[left, "x"]
    trk.loc[left, "y"] = 160 / 3 - trk.loc[left, "y"]
    return trk


def process_game(args):
    path, plays_g, routes_g = args
    trk = standardize(pd.read_csv(path, usecols=[
        "gameId", "playId", "nflId", "frameId", "time", "team", "playDirection", "x", "y", "event"]))
    rows, fps_obs = [], []
    for (gid, pid), t in trk.groupby(["gameId", "playId"]):
        if pid not in plays_g.index:
            continue
        play = plays_g.loc[pid]
        recv = routes_g.get(pid, [])
        if not recv:
            continue
        # frame rate check from coarse timestamps: frames per elapsed second over the whole play
        ts = pd.to_datetime(t.loc[t.team == "football", "time"])
        span = (ts.max() - ts.min()).total_seconds()
        nfr = t.frameId.nunique()
        if span >= 3:
            fps_obs.append((nfr - 1) / span)
        res = play_separation(t, play.possessionTeam, recv)
        if res is None:
            continue
        frames, seps, (snap, rel) = res
        ttt = (rel - snap) / 10.0
        los = t.loc[(t.team == "football") & (t.frameId == snap), "x"].mean()
        at_rel = t[t.frameId == rel].set_index("nflId")
        for r, s in seps.items():
            row = dict(gameId=gid, playId=pid, nflId=int(r), n_frames=len(frames),
                       time_to_throw=ttt, sep_release=float(s[-1]), sep_max=float(np.nanmax(s)),
                       depth_release=float(at_rel.loc[r, "x"] - los) if r in at_rel.index else np.nan)
            for k in THRESHOLDS:
                row[f"prow_{k:g}"] = open_window(s, k, 10.0)
                # open earlier for >= 0.5 s at some point, but closed at release
                above = s >= k
                runs = np.diff(np.r_[0, above.astype(int), 0])
                lengths = np.flatnonzero(runs == -1) - np.flatnonzero(runs == 1)
                row[f"lost_{k:g}"] = bool((not above[-1]) and (lengths.max(initial=0) >= 5))
            rows.append(row)
    return rows, fps_obs


def build_features(plays, scout, players) -> pd.DataFrame:
    pp = plays[plays.passResult.isin(PASS_RESULTS)].set_index(["gameId", "playId"])
    routes = scout[scout.pff_role == "Pass Route"]  # actual label in the file (README says "Pass route")
    jobs = []
    for f in sorted(TRACK_DIR.glob("tracking_*.csv")):
        gid = int(f.stem.split("_")[1])
        if gid not in pp.index.get_level_values(0):
            continue
        rg = routes[routes.gameId == gid].groupby("playId").nflId.apply(list).to_dict()
        jobs.append((f, pp.loc[gid], rg))
    if not jobs:
        sys.exit(f"No tracking files in {TRACK_DIR}. Run `python download_data.py` first.")
    print(f"Computing PROW on {len(jobs)} games ...", flush=True)
    out = []  # sequential: ~2-3 s per game; multiprocessing hung on Windows/Python 3.15
    for i, job in enumerate(jobs, 1):
        out.append(process_game(job))
        if i % 20 == 0:
            print(f"  {i}/{len(jobs)} games", flush=True)
    feats = pd.DataFrame([r for rows, _ in out for r in rows])
    fps = np.array([v for _, f in out for v in f])
    print(f"Observed frame rate (frames-1)/timestamp span: median {np.median(fps):.2f} Hz, "
          f"IQR {np.percentile(fps, 25):.2f}-{np.percentile(fps, 75):.2f} (n={len(fps)} plays)")

    assert not feats.duplicated(["gameId", "playId", "nflId"]).any()
    OUT_DIR.mkdir(exist_ok=True)
    feats.to_csv(FEATURES_CSV, index=False)
    return feats


def add_targets(feats, plays, players):
    """Flag the targeted receiver: name parsed from the play-by-play text, matched to that
    play's route runners only (so a same-initial defender can never match). Evaluation only."""
    feats = feats.drop(columns=["target_abbr", "is_target"], errors="ignore")
    names = players.set_index("nflId").displayName.map(abbrev)
    abbr = feats.nflId.map(names).str.lower()
    tgt = plays.set_index(["gameId", "playId"]).playDescription.map(parse_target).rename("target_abbr")
    feats = feats.join(tgt, on=["gameId", "playId"])
    ta = feats.target_abbr.str.lower()
    last = lambda s: s.str.split(".").str[-1]
    feats["is_target"] = ta.notna() & ((abbr == ta) | ((last(abbr) == last(ta)) & (abbr.str[0] == ta.str[0])))
    return feats


# ---------------------------------------------------------------- evaluation
BUCKETS = [-0.01, 0.0, 0.5, 1.0, 2.0, np.inf]
BUCKET_LABELS = ["0 s\n(covered at\nrelease)", "0.1-0.5 s", "0.6-1.0 s", "1.1-2.0 s", "> 2 s"]


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def game_bootstrap(df, stat, n_boot=2000, seed=0):
    """95% CI resampling whole games (plays in a game are not independent)."""
    rng = np.random.default_rng(seed)
    groups = [g for _, g in df.groupby("gameId")]
    vals = [stat(pd.concat([groups[i] for i in rng.integers(0, len(groups), len(groups))]))
            for _ in range(n_boot)]
    return np.nanpercentile(vals, [2.5, 97.5])


def targets_table(feats, plays):
    t = feats[feats.is_target].merge(
        plays[["gameId", "playId", "passResult", "pff_passCoverageType", "down", "yardsToGo"]],
        on=["gameId", "playId"], how="left", validate="many_to_one")
    # keep plays where exactly one route runner matched the parsed target
    one = t.groupby(["gameId", "playId"]).nflId.transform("size") == 1
    t = t[one].copy()
    t["complete"] = (t.passResult == "C").astype(int)
    return t


def bucket_rates(t, col):
    t = t.assign(bucket=pd.cut(t[col], BUCKETS, labels=BUCKET_LABELS))
    out = []
    for b, g in t.groupby("bucket", observed=False):
        lo, hi = wilson(g.complete.sum(), len(g))
        out.append(dict(bucket=b, n=len(g), rate=g.complete.mean(), lo=lo, hi=hi))
    return pd.DataFrame(out)


def logit_clustered(t, formula):
    import statsmodels.formula.api as smf
    return smf.logit(formula, data=t).fit(disp=0, cov_type="cluster",
                                          cov_kwds={"groups": t.gameId.astype("category").cat.codes})


if __name__ == "__main__":
    plays, scout, players, games = load_meta()
    if FEATURES_CSV.exists() and "--rebuild" not in sys.argv:
        feats = pd.read_csv(FEATURES_CSV)
    else:
        feats = build_features(plays, scout, players)
    feats = add_targets(feats, plays, players)
    import analysis
    analysis.run(feats, plays, players, games)
