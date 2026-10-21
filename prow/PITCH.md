# Pitch (~55 s)

**Hook.** Every broadcast says it: "he was wide open — why didn't the QB see him?" But *open* is a snapshot. We asked whether open *long enough* is what matters.

**Question.** When the ball leaves the quarterback's hand, does it matter how long a receiver has been open, or only whether he is open right then?

**Method.** We built PROW, the Pre-Release Open Window: how many seconds a receiver has been continuously 3 or more yards from every defender, counted back from the release. It uses only tracking between the snap and the release. The outcome of the pass is never an input; we only use it to check the metric afterwards. We applied it to 7,221 targeted throws in 122 games.

**Result.** Being open at the throw is worth about 29 points of completion rate: 76% against 47%. But an older window is not a better one. Windows less than half a second old complete 77%, and windows open more than a second complete 75%. That pattern holds whether "open" means 2, 3, 4 or 5 yards.

**So what.** The flip side is the missed window. On 24% of throws, the quarterback threw to a covered man while a teammate had been open for at least a second, and those throws were completed 48% of the time.

**Use.** The Play Lab shows the exact moment each window opened and closed, and the per-QB chart tells a QB coach which throws to put on film.

---

# Q&A cheat-sheet (all numbers from `output/summary.txt`)

- **Why this metric?** Separation at release is a snapshot. Coaches talk about a receiver "coming open" or "being open early", which are time concepts. PROW turns that into a number of seconds, so we can test it.
- **What makes it interesting?** The hypothesis failed in an informative way. Duration adds no information beyond separation at the throw (logit with game-clustered SE: PROW coefficient −0.02, p = 0.62, after separation, depth and time-to-throw). So the value is in the windows the QB *didn't* use: 24% missed windows.
- **What data?** Big Data Bowl regional data: 10 Hz tracking, plays.csv (passResult, coverage), PFF scouting (`pff_role == "Pass Route"` defines the eligible receivers). The target comes from the official play-by-play text, matched only against that play's route runners: 96.6% of descriptions were parsed, and 7,221 throws have exactly one match.
- **How many plays?** There are 7,565 C/I/IN pass plays, and 7,541 have both a snap and a release event. That gives 34,845 receiver-play rows and 7,221 targeted throws. Sacks and scrambles are excluded because there is no release to measure from.
- **Why trust it?**
  - The separation, the PROW and the time-to-throw were recomputed for 6 random receivers by an independent brute-force loop: all match exactly.
  - The frame rate was checked against the timestamps: median 10.0 Hz over 7,347 plays.
  - Confidence intervals resample whole games, because plays in the same game are not independent; no game has more than 87 throws.
  - The pattern holds at thresholds of 2, 3, 4 and 5 yards.
  - Joins are checked: unique keys and `validate="many_to_one"`.
- **Limits.**
  - The nearest defender is not necessarily the defender assigned to that receiver.
  - Being geometrically open does not make a throw possible. We do not account for the QB's progression, his sight lines, the pressure on him, or the throwing lane.
  - Correlation, not causation.
  - It covers 8 weeks of a single season.
  - Windows longer than 2 s complete a little less often (72%). We do not interpret this.
  - Each QB's rate has a ±5–6 point interval and depends on the scheme, so it is not a ranking.
- **What decision does it help?** It helps choose which film to review (missed-window plays), coach QB progressions, design routes that open at the moment the QB reaches the end of his drop, and evaluate receivers on whether they are open *at the right time* rather than open at some point.
