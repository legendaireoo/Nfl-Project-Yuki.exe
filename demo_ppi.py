#!/usr/bin/env python3
"""Yuki.exe — PPI metric demo / proof.

A tiny, dependency-free script that demonstrates the original Pocket Pressure
Index (PPI) metric straight from the tracking data, without starting the web
app. Run it to see the metric's output and sanity-check it against reality:

    python3 demo_ppi.py

(Requires the NFL dataset; see README. Honours YUKI_DATA_DIR.)
"""
from __future__ import annotations

import metrics


def main() -> None:
    print("=" * 66)
    print("  PPI — Pocket Pressure Index   (demo over the first 15 games)")
    print("=" * 66)
    print(
        "PFF logs only a binary hit/hurry/sack. PPI instead scores, 0-100, how\n"
        "much heat the QB actually felt, from snap-to-throw tracking geometry:\n"
        "  proximity (exponential) x closing speed x pocket urgency.\n"
    )

    lb = metrics.leaderboard(15)
    print(f"Dropbacks scored: {lb['playsScored']}   League average PPI: {lb['avgPPI']}\n")

    print("TOP 10 PPI GENERATORS (pass rushers)")
    print(f"  {'#':>2}  {'Player':22s} {'Pos':4s} {'Plays':>5s} {'TotalPPI':>9s} {'PPI/Play':>9s}")
    for i, r in enumerate(lb["rushers"][:10], 1):
        print(f"  {i:>2}  {r['name']:22s} {r['position']:4s} {r['plays']:>5d}"
              f" {r['totalPPI']:>9.1f} {r['ppiPerPlay']:>9.2f}")

    print("\nTOP 8 GHOST PRESSURE  (PPI on plays the box score credits to nobody)")
    print(f"  {'#':>2}  {'Player':22s} {'GhostPPI':>9s} {'Plays':>6s}")
    for i, r in enumerate(lb["ghostLeaders"][:8], 1):
        print(f"  {i:>2}  {r['name']:22s} {r['ghostPPI']:>9.1f} {r['ghostPlays']:>6d}")

    print("\nMOST PRESSURING DEFENSES (avg PPI forced):",
          ", ".join(f"{t['team']} {t['avgPPI']}" for t in lb["teamsDefense"][:5]))
    print("BEST-PROTECTED OFFENSES (lowest PPI faced):",
          ", ".join(f"{t['team']} {t['avgPPI']}" for t in lb["teamsOffense"][:5]))

    top = lb["topPlays"][0]
    print(f"\nHIGHEST-PPI PLAY: PPI {top['ppi']} | {top['def']} rush vs {top['off']}"
          f" | throw in {top['timeToThrow']}s"
          f" | game {top['gameId']} play {top['playId']}")
    print("\n(Elite real-world rushers topping the board = the metric passes the eye test.)")


if __name__ == "__main__":
    main()
