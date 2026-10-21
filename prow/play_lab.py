"""Play Lab: one play on a real-coordinate field + receiver separation timeline (snap -> release)."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

import prow

OFF, DEF, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#d9d8d3"
SURFACE = "#fcfcfb"


def load_play(gid, pid):
    trk = pd.read_csv(prow.TRACK_DIR / f"tracking_{gid}.csv")
    return prow.standardize(trk[trk.playId == pid])


def draw_field(ax, x0, x1):
    ax.add_patch(Rectangle((x0, 0), x1 - x0, 160 / 3, color="#eef3ea", zorder=0))
    ax.add_patch(Rectangle((110, 0), 10, 160 / 3, color="#dfe7d8", zorder=0))  # opponent end zone
    for x in range(10, 111, 5):
        if x0 <= x <= x1:
            ax.axvline(x, color="white", lw=1.6 if x % 10 == 0 else 0.8, zorder=1)
            if x % 10 == 0 and 10 < x < 110:
                yd = x - 10 if x <= 60 else 110 - x
                ax.text(x, 4, str(yd), ha="center", va="center", color="#b9c4b2", fontsize=11, zorder=1)
    ax.set_xlim(x0, x1)
    ax.set_ylim(0, 160 / 3)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def play_lab(gid, pid, plays, players, feats, out_path, k=prow.PRIMARY_K, highlight=None):
    t = load_play(gid, pid)
    play = plays[(plays.gameId == gid) & (plays.playId == pid)].iloc[0]
    offense = play.possessionTeam
    ball = t[t.team == "football"]
    ev = ball.dropna(subset=["event"]).set_index("event").frameId
    snap = ev[ev.index.isin(prow.SNAP_EVENTS)].min()
    rel = ev[ev.index.isin(prow.RELEASE_EVENTS)].min()
    f = feats[(feats.gameId == gid) & (feats.playId == pid)]
    recv = f.nflId.tolist()
    frames, seps, _ = prow.play_separation(t, offense, recv)
    tsec = (frames - snap) / 10.0
    names = players.set_index("nflId").displayName
    target = f.loc[f.is_target, "nflId"]
    target = int(target.iloc[0]) if len(target) else None
    highlight = highlight or []

    ALT = "#6250d6"
    fig = plt.figure(figsize=(16, 8.2), dpi=150, facecolor=SURFACE)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1], wspace=0.12, left=0.03, right=0.88, top=0.80, bottom=0.10)
    ax = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1])

    w = t[(t.frameId >= snap) & (t.frameId <= rel)]
    los = ball.loc[ball.frameId == snap, "x"].iloc[0]
    draw_field(ax, max(0, los - 12), min(120, los + 45))
    ax.axvline(los, color=MUTED, lw=1, ls="--", zorder=2)
    for nid, g in w[w.team != "football"].groupby("nflId"):
        is_off = g.team.iloc[0] == offense
        key = nid == target or nid in highlight
        col = ALT if nid in highlight else (OFF if is_off else DEF)
        ax.plot(g.x, g.y, color=col, lw=2.6 if key else 1, alpha=1 if key else 0.45, zorder=3)
        end = g[g.frameId == rel]
        ax.scatter(end.x, end.y, s=140 if key else 45, color=col, edgecolor="white", lw=1.5, zorder=4)
        if key:
            ax.annotate(names.get(nid, "") + (" (target)" if nid == target else " (open teammate)"),
                        (end.x.iloc[0], end.y.iloc[0]), xytext=(8, 8), textcoords="offset points",
                        fontsize=10.5, color=INK, weight="bold", zorder=5,
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))
    bw = ball[(ball.frameId >= snap) & (ball.frameId <= rel)]
    ax.plot(bw.x, bw.y, color="#7a5a2b", lw=1.2, zorder=3)
    ax.set_title("Paths snap -> release (offense blue, defense orange; dots = release)\n"
                 "offense drives left -> right; dashed line = line of scrimmage", loc="left", fontsize=10.5, color=MUTED)

    order = sorted(seps, key=lambda r: (r == target or r in highlight))
    for r in order:
        s = seps[r]
        key = r == target or r in highlight
        col = OFF if r == target else (ALT if r in highlight else "#b5b4ad")
        ax2.plot(tsec, s, color=col, lw=2.6 if key else 1, alpha=1 if key else 0.8)
        if key:
            pw = f.loc[f.nflId == r, f"prow_{k:g}"].iloc[0]
            ax2.annotate(f"{names.get(r, r)}\n{s[-1]:.1f} yd at release\nPROW = {pw:.1f} s", (tsec[-1], s[-1]),
                         xytext=(10, 0), textcoords="offset points", va="center", fontsize=10, color=INK)
            if pw > 0:
                ax2.axvspan(max(0, tsec[-1] - pw), tsec[-1], color=col, alpha=0.08)
    ax2.axhline(k, color=INK, lw=1, ls=":")
    ax2.text(0, k + 0.2, f"open threshold = {k:g} yd", fontsize=9, color=MUTED)
    ax2.axvline(tsec[-1], color=INK, lw=1)
    ax2.text(tsec[-1], ax2.get_ylim()[1] * 0.97, " release", fontsize=9, color=INK, va="top")
    ax2.set_title("Distance to nearest defender, every route runner (shaded = PROW window)",
                  loc="left", fontsize=10.5, color=MUTED)
    ax2.set_ylim(0, None)
    ax2.set_xlabel("Time since snap (s)")
    ax2.set_ylabel("Distance to nearest defender (yd)")
    ax2.set_facecolor(SURFACE)
    ax2.grid(axis="y", color=GRID, lw=0.6)
    for s in ["top", "right"]:
        ax2.spines[s].set_visible(False)
    res = {"C": "Complete", "I": "Incomplete", "IN": "Intercepted"}[play.passResult]
    fig.suptitle(f"Play Lab - {play.possessionTeam} vs {play.defensiveTeam}, Q{play.quarter} "
                 f"{int(play.down)}&{int(play.yardsToGo)}  |  outcome: {res}",
                 x=0.03, ha="left", fontsize=16, weight="bold", color=INK, y=0.97)
    fig.text(0.03, 0.885, str(play.playDescription)[:170], fontsize=10, color=MUTED)
    fig.savefig(out_path, facecolor=SURFACE)
    plt.close(fig)
    return out_path
