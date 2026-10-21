"""Build output/YUKI_report.html: one self-contained page (figures embedded) for the jury.
All numbers come from output/headline.json written by `python prow.py`."""
import base64
import json
from pathlib import Path

OUT = Path(__file__).parent / "output"


def img(name):
    return "data:image/png;base64," + base64.b64encode((OUT / name).read_bytes()).decode()


def pct(x):
    return f"{x * 100:.0f}%"


def build():
    h = json.loads((OUT / "headline.json").read_text(encoding="utf-8"))
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>YUKI - Open But Unreachable?</title>
<style>
:root {{ color-scheme: light; --ink:#0b0b0b; --muted:#52514e; --line:#e4e3de; --surface:#fcfcfb; --page:#f4f3ef;
  --off:#2a78d6; --def:#eb6834; --alt:#6250d6; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--page); color:var(--ink); font:16px/1.5 "Segoe UI",system-ui,sans-serif; }}
main {{ max-width:1180px; margin:0 auto; padding:28px 16px 60px; }}
header h1 {{ font-size:clamp(28px,4vw,42px); margin:0 0 4px; letter-spacing:-.5px; }}
header .tag {{ color:var(--muted); font-size:15px; margin:0 0 6px; text-transform:uppercase; letter-spacing:1.5px; font-weight:600; }}
header .q {{ font-size:clamp(18px,2.2vw,22px); margin:6px 0 24px; max-width:860px; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:14px; margin-bottom:28px; }}
.tile {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:18px 20px; }}
.tile .big {{ font-size:44px; font-weight:700; line-height:1.1; }}
.tile .lbl {{ font-weight:600; margin:6px 0 4px; }}
.tile .sub {{ color:var(--muted); font-size:14px; }}
.b-off {{ border-top:4px solid var(--off); }} .b-mid {{ border-top:4px solid #a3a29c; }} .b-def {{ border-top:4px solid var(--def); }}
section {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:20px; margin-bottom:22px; }}
section h2 {{ margin:0 0 4px; font-size:21px; }}
section .how {{ color:var(--muted); margin:0 0 14px; font-size:15px; }}
section img {{ width:100%; height:auto; display:block; border-radius:6px; }}
.step {{ display:inline-block; background:var(--ink); color:#fff; border-radius:999px; width:26px; height:26px;
  text-align:center; line-height:26px; font-size:14px; margin-right:8px; }}
details {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:14px 20px; margin-bottom:14px; }}
summary {{ cursor:pointer; font-weight:600; }}
details li {{ margin:4px 0; }}
footer {{ color:var(--muted); font-size:13px; margin-top:24px; }}
code {{ background:#eceae4; padding:1px 5px; border-radius:4px; }}
</style></head><body><main>
<header>
 <p class="tag">YUKI &middot; NFL Big Data Bowl tracking &middot; 2021 weeks 1-8</p>
 <h1>Open But Unreachable?</h1>
 <p class="q">When the quarterback throws, does it matter <b>how long</b> a receiver has been open, or only
 <b>whether</b> he is open at that instant? We measure it with <b>PROW</b>, the Pre-Release Open Window:
 the number of seconds a receiver has been continuously at least 3 yards from every defender, counted back from the release.</p>
</header>

<div class="tiles">
 <div class="tile b-off"><div class="big">+{h['diff'] * 100:.0f} pts</div>
  <div class="lbl">completion rate when the target is open at the throw</div>
  <div class="sub">{pct(h['open_rate'])} open vs {pct(h['covered_rate'])} covered &middot; 95% CI +{h['diff_lo'] * 100:.0f} to +{h['diff_hi'] * 100:.0f}</div></div>
 <div class="tile b-mid"><div class="big">&asymp; 0</div>
  <div class="lbl">extra value of a window that has been open for longer</div>
  <div class="sub">open &le; 0.5 s: {pct(h['fresh_rate'])} &middot; open &gt; 1 s: {pct(h['old_rate'])} &middot; adjusted p = {h['prow_p']:.2f}</div></div>
 <div class="tile b-def"><div class="big">{pct(h['missed'])}</div>
  <div class="lbl">of throws go to a covered target while a teammate has been open &ge; 1 s</div>
  <div class="sub">those throws complete only {pct(h['missed_completion'])} &middot; n = {h['n_missed']:,}</div></div>
</div>

<section><h2><span class="step">1</span>The proof: being open at the throw matters, how long it has been open does not</h2>
 <p class="how">Each bar is the completion rate of the targeted receiver, grouped by his PROW. Orange = covered at release.
 The blue bars are flat, so a window that has been open for longer is not a better one. Panel B shows the same pattern for any "open" threshold between 2 and 5 yards.</p>
 <img src="{img('fig1_prow_main.png')}" alt="Completion rate by PROW bucket"></section>

<section><h2><span class="step">2</span>Play Lab: what a missed window looks like</h2>
 <p class="how">On the left, the real paths from snap to release. On the right, each receiver's distance to the nearest defender over time.
 The QB targeted {h['ex_target']}, who was {h['ex_target_sep']:.1f} yd from a defender at release, while {h['ex_alt']}
 had been open for {h['ex_alt_prow']:.1f} s.</p>
 <img src="{img('fig2_play_lab.png')}" alt="Play Lab example"></section>

<section><h2><span class="step">3</span>Use it: missed-window rate by quarterback</h2>
 <p class="how">This is a film-review list, not a ranking: the intervals overlap. It covers {h['n_qbs']} QBs with at least 150 throws, whose rates range from {pct(h['qb_min'])} to {pct(h['qb_max'])}.</p>
 <img src="{img('fig3_missed_windows_by_qb.png')}" alt="Missed-window rate by QB"></section>

<details><summary>Method</summary><ul>
 <li>Data: {h['n_throws']:,} targeted throws in {h['n_games']} games (complete, incomplete and intercepted passes with a snap and a release in the tracking). Sacks and scrambles are excluded because there is no release to measure from.</li>
 <li>Route runners come from PFF <code>pff_role = "Pass Route"</code>. The targeted receiver is parsed from the official play-by-play text and matched only against that play's route runners.</li>
 <li>PROW uses only tracking frames between the snap and the release, at 10 Hz (checked against the timestamps). Pass outcomes are used only to evaluate the metric.</li>
 <li>Uncertainty: confidence intervals resample whole games. The logistic regression uses standard errors clustered by game and controls for separation at release, depth and time to throw.</li>
 <li>Checks: separation, PROW and time to throw were recomputed with an independent brute-force loop on random receivers, and all match exactly.</li></ul></details>
<details><summary>Limits</summary><ul>
 <li>The nearest defender is not necessarily the defender assigned to that receiver.</li>
 <li>Being geometrically open is not the same as being reachable: we do not model the QB's progression, his sight lines, the pass rush or the throwing lane.</li>
 <li>These are associations, not causal effects. The data cover 8 weeks of a single season.</li></ul></details>
<footer>Reproduce: <code>pip install -r requirements.txt</code> &rarr; <code>python download_data.py</code> &rarr; <code>python prow.py</code>.</footer>
</main></body></html>"""
    out = OUT / "YUKI_report.html"
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build())
