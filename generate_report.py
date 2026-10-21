#!/usr/bin/env python3
"""Yuki.exe — one-shot visual report generator (no browser, no dependencies).

Produces a shareable, self-contained **SVG infographic** of the PPI metric that
you can open in any browser or drop straight into a submission / slide. This is
the "visualisation / capture of the tool" deliverable, generated from the data
with the standard library only.

    python3 generate_report.py            # -> ppi_report.svg
    python3 generate_report.py out.svg    # custom path

Open the .svg in a browser and (optionally) "Save as PNG" / screenshot it.
"""
from __future__ import annotations

import html
import sys

import metrics

W, H = 1000, 720
BG = "#0b0f17"
PANEL = "#141b27"
ACCENT = "#4f9dff"
GOLD = "#ffbf47"
RED = "#ff6b6b"
GREEN = "#37d6a0"
TEXT = "#e6edf6"
MUTED = "#8c9bb3"


def esc(s: str) -> str:
    return html.escape(str(s))


def bar_row(x, y, w, label, value, maxv, color, vfmt=None):
    frac = (value / maxv) if maxv else 0
    bw = max(2, frac * w)
    vtxt = vfmt(value) if vfmt else str(value)
    return (
        f'<text x="{x - 8}" y="{y + 11}" fill="{TEXT}" font-size="13" '
        f'text-anchor="end" font-family="Segoe UI, sans-serif">{esc(label)}</text>'
        f'<rect x="{x}" y="{y}" width="{bw:.1f}" height="15" rx="4" fill="{color}"/>'
        f'<text x="{x + bw + 6:.1f}" y="{y + 12}" fill="{MUTED}" font-size="12" '
        f'font-family="Segoe UI, sans-serif">{esc(vtxt)}</text>'
    )


def build_svg(lb: dict) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="Segoe UI, sans-serif">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        # header
        f'<text x="40" y="52" fill="{TEXT}" font-size="30" font-weight="700">'
        f'🏈 Yuki.exe — PPI: Pocket Pressure Index</text>',
        f'<text x="40" y="78" fill="{MUTED}" font-size="14">An original tracking-derived metric · '
        f'{lb["playsScored"]} dropbacks scored across {lb["gamesAnalyzed"]} games · '
        f'league avg PPI {lb["avgPPI"]}</text>',
        f'<rect x="40" y="92" width="{W-80}" height="2" fill="{ACCENT}" opacity="0.5"/>',
    ]

    # Panel 1: top PPI generators
    rushers = lb["rushers"][:10]
    maxr = max((r["totalPPI"] for r in rushers), default=1)
    parts.append(f'<text x="40" y="128" fill="{GOLD}" font-size="17" font-weight="700">'
                 f'Top PPI Generators (pass rushers)</text>')
    y = 150
    bx = 190
    bw = 300
    for r in rushers:
        parts.append(bar_row(bx, y, bw, f'{r["name"]} ({r["position"]})',
                             r["totalPPI"], maxr, ACCENT))
        y += 24

    # Panel 2: ghost pressure
    ghosts = lb["ghostLeaders"][:10]
    maxg = max((r["ghostPPI"] for r in ghosts), default=1)
    parts.append(f'<text x="540" y="128" fill="{GOLD}" font-size="17" font-weight="700">'
                 f'👻 Ghost Pressure (box score misses this)</text>')
    y = 150
    bx2 = 690
    bw2 = 270
    for r in ghosts:
        parts.append(bar_row(bx2, y, bw2, r["name"], r["ghostPPI"], maxg, RED))
        y += 24

    # Panel 3: defenses
    defs = lb["teamsDefense"][:8]
    maxd = max((t["avgPPI"] for t in defs), default=1)
    parts.append(f'<text x="40" y="440" fill="{GOLD}" font-size="17" font-weight="700">'
                 f'Most Pressuring Defenses (avg PPI forced)</text>')
    y = 462
    for t in defs:
        parts.append(bar_row(110, y, 360, t["team"], t["avgPPI"], maxd, RED))
        y += 24

    # Panel 4: offenses
    offs = lb["teamsOffense"][:8]
    maxo = max((t["avgPPI"] for t in offs), default=1)
    parts.append(f'<text x="540" y="440" fill="{GOLD}" font-size="17" font-weight="700">'
                 f'Best-Protected Offenses (lowest PPI faced)</text>')
    y = 462
    for t in offs:
        parts.append(bar_row(610, y, 330, t["team"], t["avgPPI"], maxo, GREEN))
        y += 24

    # footer / explainer
    parts.append(
        f'<text x="40" y="690" fill="{MUTED}" font-size="12.5">'
        f'PPI = proximity (exp.) × closing speed × pocket urgency, measured frame-by-frame '
        f'from snap to throw. Elite real rushers top the board = the metric passes the eye test.'
        f'</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "ppi_report.svg"
    print("Computing PPI across the first 20 games (reading raw tracking)...")
    lb = metrics.leaderboard(20)
    svg = build_svg(lb)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"Saved infographic -> {out}")
    print("Open it in any browser; use 'Save as image' / screenshot for a PNG.")


if __name__ == "__main__":
    main()
