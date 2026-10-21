"""Statistics + figures for PROW. Called from prow.py (python prow.py)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import prow
from play_lab import DEF, GRID, INK, MUTED, OFF, SURFACE, play_lab

KEY = ["gameId", "playId"]
K = prow.PRIMARY_K
ALT_MIN = 1.0  # seconds a teammate must have been open for a "missed window"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlecolor": INK})


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)


def with_alternatives(feats, t, k=K):
    """Add, for each targeted throw, the best pre-release window among the OTHER route runners."""
    col = f"prow_{k:g}"
    other = feats[~feats.is_target].sort_values(col).groupby(KEY).tail(1)
    other = other.set_index(KEY)[[col, "depth_release", "sep_release", "nflId"]].add_prefix("alt_")
    t = t.merge(other, left_on=KEY, right_index=True, how="left", validate="one_to_one")
    t["missed"] = ((t[col] == 0) & (t[f"alt_{col}"] >= ALT_MIN)).astype(int)
    return t


def fig_main(t, feats, plays, out):
    fig, axes = plt.subplots(1, 2, figsize=(16, 7.5), dpi=150, facecolor=SURFACE,
                             gridspec_kw={"width_ratios": [1.45, 1], "wspace": 0.22})
    # A: completion by PROW bucket, primary threshold
    ax = axes[0]; style(ax)
    br = prow.bucket_rates(t, f"prow_{K:g}")
    xs = np.arange(len(br))
    cols = [DEF] + [OFF] * (len(br) - 1)
    ax.bar(xs, br.rate * 100, width=0.62, color=cols, zorder=2)
    ax.errorbar(xs, br.rate * 100, yerr=[(br.rate - br.lo) * 100, (br.hi - br.rate) * 100],
                fmt="none", ecolor=INK, elinewidth=1.2, capsize=4, zorder=3)
    for x, r in zip(xs, br.itertuples()):
        ax.text(x, r.hi * 100 + 1.5, f"{r.rate:.0%}", ha="center", fontsize=13, weight="bold", color=INK)
        ax.text(x, 3, f"n={r.n:,}", ha="center", fontsize=9.5, color="white", weight="bold")
    ax.set_xticks(xs, br.bucket, fontsize=10.5)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Completion rate of the targeted receiver (%)")
    ax.set_xlabel(f"PROW: how long the target had been >= {K:g} yd from every defender when the ball left (s)")
    ax.set_title("A. Open AT the throw matters - how long it was open does not",
                 loc="left", fontsize=13, weight="bold")
    ax.text(0, br.rate[0] * 100 / 2, "covered\nat release", ha="center", fontsize=10, color="white", weight="bold")
    top = max(br.hi.iloc[1:]) * 100 + 8
    ax.plot([0.75, 4.25], [top, top], color=MUTED, lw=1, ls="--")
    ax.text(2.5, top + 1.5, "no gain from a longer window: an older window is not a better window",
            ha="center", fontsize=10, color=MUTED, style="italic")

    # B: sensitivity to the threshold k
    ax = axes[1]; style(ax)
    markers = {2.0: "o", 3.0: "s", 4.0: "D", 5.0: "^"}
    shades = {2.0: "#86b6ef", 3.0: OFF, 4.0: "#1c5cab", 5.0: "#0d366b"}
    for k in prow.THRESHOLDS:
        b = prow.bucket_rates(t, f"prow_{k:g}")
        ax.plot(xs, b.rate * 100, marker=markers[k], ms=8, lw=2, color=shades[k],
                markeredgecolor="white", label=f"k = {k:g} yd")
    ax.set_xticks(xs, ["0", "0.1-0.5", "0.6-1.0", "1.1-2.0", "> 2"], fontsize=10.5)
    ax.set_ylim(35, 90)
    ax.set_xlabel("PROW bucket (s)")
    ax.set_ylabel("Completion rate (%)")
    ax.set_title("B. Same shape for every 'open' threshold", loc="left", fontsize=13, weight="bold")
    ax.legend(frameon=False, loc="lower right", title="open = separation >=", title_fontsize=9)

    n_games, n_t = t.gameId.nunique(), len(t)
    fig.suptitle("OPEN BUT UNREACHABLE?  Pre-Release Open Window (PROW) vs. pass outcome",
                 x=0.06, ha="left", fontsize=19, weight="bold", color=INK, y=0.995)
    fig.text(0.06, 0.915, f"{n_t:,} targeted throws, {n_games} games, 2021 NFL weeks 1-8 (Big Data Bowl tracking, 10 Hz). "
             "PROW uses only snap-to-release tracking; outcomes are used only to evaluate it. "
             "Error bars: 95% Wilson CI.", fontsize=10, color=MUTED)
    fig.subplots_adjust(top=0.83, bottom=0.12, left=0.06, right=0.98)
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def fig_missed(t, qb_names, out):
    """Missed-window rate per QB (throws to a covered target while a teammate had been open >= 1 s)."""
    q = t.groupby("qbId").agg(n=("missed", "size"), rate=("missed", "mean")).query("n >= 150")
    rng = np.random.default_rng(1)
    ci = []
    for qb in q.index:
        m = t.loc[t.qbId == qb, "missed"].values
        bs = rng.choice(m, (2000, len(m))).mean(1)
        ci.append(np.percentile(bs, [2.5, 97.5]))
    q[["lo", "hi"]] = np.array(ci)
    q = q.sort_values("rate")
    league = t.missed.mean()
    fig, ax = plt.subplots(figsize=(11, max(6, 0.32 * len(q) + 2)), dpi=150, facecolor=SURFACE)
    style(ax); ax.grid(axis="x", color=GRID, lw=0.6); ax.grid(axis="y", visible=False)
    ys = np.arange(len(q))
    ax.hlines(ys, q.lo * 100, q.hi * 100, color="#b7d3f6", lw=4, zorder=2)
    ax.scatter(q.rate * 100, ys, s=70, color=OFF, edgecolor="white", lw=1.5, zorder=3)
    ax.axvline(league * 100, color=DEF, lw=1.5, ls="--", zorder=1)
    ax.text(league * 100, len(q) - 0.2, f" all throws {league:.0%}", color=INK, fontsize=10, va="bottom")
    ax.set_yticks(ys, [f"{qb_names.get(i, i)}  (n={n})" for i, n in zip(q.index, q.n)], fontsize=9.5)
    ax.set_xlabel(f"% of throws to a target covered at release (< {K:g} yd) while a teammate had been open >= {ALT_MIN:g} s")
    ax.set_title("Missed-window rate by QB\n(QBs with >= 150 targeted throws, dot = rate, bar = 95% bootstrap CI)",
                 loc="left", fontsize=12.5, weight="bold")
    fig.text(0.01, 0.005, "Descriptive, not a grade: an open teammate may be outside the QB's progression, behind him, or "
             "unreachable under pressure. Use it to pick film to review.", fontsize=8.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    return q


def pick_example(t, plays):
    """Incomplete throw (no penalty) to a tightly covered target while a downfield teammate had a long open window."""
    clean = plays.loc[plays.foulName1.isna(), KEY]
    t = t.merge(clean, on=KEY)
    c = t[(t.missed == 1) & (t.passResult == "I") & (t.sep_release < 1.5) & (t[f"alt_prow_{K:g}"] >= 2)
          & t.alt_depth_release.between(5, 20) & t.time_to_throw.between(2.3, 3.5)]
    return c.sort_values(f"alt_prow_{K:g}", ascending=False).iloc[0]


def run(feats, plays, players, games):
    prow.OUT_DIR.mkdir(exist_ok=True)
    lines = []
    say = lambda s="": (print(s), lines.append(s))
    t = prow.targets_table(feats, plays)
    t = with_alternatives(feats, t)
    pass_plays = plays.passResult.isin(prow.PASS_RESULTS).sum()
    say(f"Pass plays (C/I/IN) in plays.csv: {pass_plays}; with snap+release in tracking: {feats.groupby(KEY).ngroups}")
    say(f"Route-runner rows: {len(feats)}; targeted throws matched to exactly one route runner: {len(t)} "
        f"({t.gameId.nunique()} games, max {t.groupby('gameId').size().max()} per game)")
    col = f"prow_{K:g}"
    say(f"\nCompletion by PROW bucket (k={K:g} yd):")
    say(prow.bucket_rates(t, col).assign(bucket=lambda d: d.bucket.str.replace("\n", " ")).round(3).to_string(index=False))
    op, cv = t[t[col] > 0], t[t[col] == 0]
    diff = op.complete.mean() - cv.complete.mean()
    lo, hi = prow.game_bootstrap(t, lambda d: d[d[col] > 0].complete.mean() - d[d[col] == 0].complete.mean())
    head = dict(n_throws=len(t), n_games=int(t.gameId.nunique()), open_rate=op.complete.mean(), n_open=len(op),
                covered_rate=cv.complete.mean(), n_covered=len(cv), diff=diff, diff_lo=lo, diff_hi=hi)
    say(f"Open at release {op.complete.mean():.1%} (n={len(op)}) vs covered {cv.complete.mean():.1%} (n={len(cv)}): "
        f"+{diff * 100:.1f} pts, game-bootstrap 95% CI [{lo * 100:.1f}, {hi * 100:.1f}]")
    fresh, old = op[op[col] <= 0.5], op[op[col] > 1.0]
    lo, hi = prow.game_bootstrap(op, lambda d: d[d[col] > 1.0].complete.mean() - d[d[col] <= 0.5].complete.mean())
    head.update(old_rate=old.complete.mean(), n_old=len(old), fresh_rate=fresh.complete.mean(), n_fresh=len(fresh),
                age_lo=lo, age_hi=hi)
    say(f"Among open targets: window > 1 s {old.complete.mean():.1%} (n={len(old)}) vs fresh <= 0.5 s "
        f"{fresh.complete.mean():.1%} (n={len(fresh)}): diff {(old.complete.mean() - fresh.complete.mean()) * 100:+.1f} pts, "
        f"95% CI [{lo * 100:.1f}, {hi * 100:.1f}]")
    d = t.dropna(subset=["depth_release"])
    for form in ["complete ~ sep_release", f"complete ~ sep_release + {col} + depth_release + time_to_throw"]:
        m = prow.logit_clustered(d, form)
        if col in m.params:
            head.update(prow_coef=m.params[col], prow_p=m.pvalues[col])
        say(f"Logit (game-clustered SE) {form}: " + ", ".join(
            f"{k}={v:+.3f} (p={m.pvalues[k]:.3g})" for k, v in m.params.items() if k != "Intercept"))
    say("\nSensitivity (open at release vs covered, all k):")
    for k in prow.THRESHOLDS:
        c = f"prow_{k:g}"
        say(f"  k={k:g}: open {t[t[c] > 0].complete.mean():.1%} (n={(t[c] > 0).sum()}), "
            f"covered {t[t[c] == 0].complete.mean():.1%} (n={(t[c] == 0).sum()})")

    lo, hi = prow.game_bootstrap(t, lambda d: d.missed.mean())
    mt = t[t.missed == 1]
    head.update(missed=t.missed.mean(), n_missed=len(mt), missed_lo=lo, missed_hi=hi,
                missed_completion=mt.complete.mean())
    say(f"\nMissed windows (target < {K:g} yd at release, teammate open >= {ALT_MIN:g} s): "
        f"{t.missed.mean():.1%} of throws (n={len(mt)}), game-bootstrap 95% CI [{lo:.1%}, {hi:.1%}]")
    say(f"  completion on those throws {mt.complete.mean():.1%}; open teammate median depth "
        f"{mt.alt_depth_release.median():.1f} yd past LOS, {(mt.alt_depth_release >= 0).mean():.0%} downfield; "
        f"median separation {mt.alt_sep_release.median():.1f} yd")
    say("  by coverage: " + ", ".join(f"{k} {v.mean():.1%} (n={len(v)})" for k, v in t.groupby("pff_passCoverageType").missed))
    say(f"Route runners open >= 0.5 s at some point but covered at release: {feats[f'lost_{K:g}'].mean():.1%}")

    qb = (prow.pd.read_csv(prow.DATA_DIR / "pffScoutingData.csv", usecols=["gameId", "playId", "nflId", "pff_role"])
          .query("pff_role == 'Pass'").drop_duplicates(KEY).rename(columns={"nflId": "qbId"})[KEY + ["qbId"]])
    t = t.merge(qb, on=KEY, how="left", validate="many_to_one")
    names = players.set_index("nflId").displayName

    fig_main(t, feats, plays, prow.OUT_DIR / "fig1_prow_main.png")
    q = fig_missed(t, names, prow.OUT_DIR / "fig3_missed_windows_by_qb.png")
    say(f"\nQB table (n>=150 throws): {len(q)} QBs, missed-window rate range {q.rate.min():.1%}-{q.rate.max():.1%}")
    ex = pick_example(t, plays)
    play_lab(int(ex.gameId), int(ex.playId), plays, players, feats, prow.OUT_DIR / "fig2_play_lab.png",
             highlight=[int(ex.alt_nflId)])
    say(f"Play Lab example: gameId={int(ex.gameId)} playId={int(ex.playId)} target sep {ex.sep_release:.1f} yd, "
        f"teammate {names.get(int(ex.alt_nflId))} PROW {ex[f'alt_prow_{K:g}']:.1f} s")
    head.update(n_qbs=len(q), qb_min=q.rate.min(), qb_max=q.rate.max(),
                ex_target=names.get(int(ex.nflId)), ex_target_sep=ex.sep_release,
                ex_alt=names.get(int(ex.alt_nflId)), ex_alt_prow=ex[f"alt_prow_{K:g}"])
    import json
    (prow.OUT_DIR / "headline.json").write_text(
        json.dumps({k: (v.item() if hasattr(v, "item") else v) for k, v in head.items()}, indent=1), encoding="utf-8")
    t.to_csv(prow.OUT_DIR / "targeted_throws.csv", index=False)
    (prow.OUT_DIR / "summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote figures + summary to {prow.OUT_DIR}")
