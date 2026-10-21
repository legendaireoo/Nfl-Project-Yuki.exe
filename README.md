# 🏈 Yuki.exe — NFL Big Data Bowl Analytics

An interactive web app to **analyze the NFL Big Data Bowl (regional event) dataset** —
pass-rush production, pass protection, defensive coverages, team trends, and a
frame-by-frame **play animation viewer** built straight from the player-tracking data.

Data source:
[ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data](https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data)
(tracking by NFL Next Gen Stats, scouting by PFF).

## ✨ Why it's special

**Zero dependencies.** No `pip install`, no `npm install`, no internet needed.
The backend uses only the Python standard library (`http.server` + `csv`) and the
frontend is vanilla HTML/CSS/JS with charts drawn on `<canvas>`. If you have Python 3,
you can run it.

## 📊 Features

| View | What it shows |
|------|---------------|
| **Overview** | Headline stats (plays, completion %, pressures, sacks) + donut of coverage usage, dropback outcomes, and offensive formations |
| **Coverages** | Completion % allowed and avg yards for every PFF coverage scheme (Cover-0 … Prevent) |
| **Pass Rush** | Leaderboard of top disruptors — hits, hurries, sacks, total pressures & pressure rate |
| **Pass Block** | Best protectors — lowest pressure-allowed rate (min. 50 snaps) |
| **Teams** | Scatter of team pass-rush rate vs. pressure-allowed rate, with full table |
| **Play Viewer** | Pick any game + play and **animate the tracking data** on a football field — players colored by offense/defense, ball, direction arrows, line of scrimmage, and live event tags (snap, pass release, tackle…) |

## 🚀 Running it

### ⭐ Easiest — one click (auto-everything)

These launchers **find Python, download the dataset the first time if it's
missing, start the server, pick a free port, and open your browser** — all
automatically.

| OS | Do this |
|----|---------|
| **Windows** | Double-click **`Start-Yuki.bat`** |
| **macOS / Linux** | Run **`./start-yuki.sh`** (or `bash start-yuki.sh`) |
| **Any OS** | `python3 launch.py` |

That's it — the dashboard opens at `http://127.0.0.1:8000` by itself.
(First launch clones the ~800 MB dataset with `git`; later launches are instant.)

### 🏗️ Build a true standalone `Yuki.exe` (no Python needed by the user)

```bash
pip install pyinstaller
python build_exe.py
```

This produces a single self-contained binary in `dist/`:
`Yuki.exe` on Windows, `Yuki` on macOS/Linux. Ship that one file — the user
just double-clicks it. On first run it fetches the dataset automatically
(needs `git` + internet, one time). Build on the OS you want to target.

### 🔧 Manual (classic) start

```bash
# By default Yuki looks for the dataset at
#   ../nfl-big-data-bowl-regional-event-data/data  (next to this repo).
# To point somewhere else:
export YUKI_DATA_DIR=/path/to/nfl-big-data-bowl-regional-event-data/data

python3 server.py        # then open http://127.0.0.1:8000
```

Optional environment variables:

| Var | Default | Purpose |
|-----|---------|---------|
| `YUKI_DATA_DIR` | `../nfl-big-data-bowl-regional-event-data/data` | Location of the CSV dataset |
| `YUKI_HOST` | `127.0.0.1` | Bind host |
| `YUKI_PORT` | `8000` | Bind port |

## 🗂️ Project structure

```
Nfl-Project-Yuki.exe/
├── launch.py        # ⭐ one-click launcher: find data, start server, open browser
├── Start-Yuki.bat   # Windows double-click launcher
├── start-yuki.sh    # macOS / Linux launcher
├── build_exe.py     # builds a standalone Yuki.exe via PyInstaller
├── server.py        # stdlib HTTP server: static files + JSON API
├── analytics.py     # all the stat computations (coverage, pressure, teams, plays)
├── data_loader.py   # CSV parsing + caching (no pandas)
├── config.py        # paths & constants
└── web/
    ├── index.html   # single-page UI shell
    ├── style.css    # dark NFL-themed styling
    ├── charts.js    # canvas chart helpers (bar, donut, scatter)
    ├── field.js     # football-field renderer + play animation
    └── app.js       # frontend controller / API wiring
```

## 🔌 API endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/overview` | Dataset-wide summary stats |
| `GET /api/coverage` | Per-coverage efficiency |
| `GET /api/pass-rush` | Pass-rush leaderboard |
| `GET /api/pass-block` | Pass-protection leaderboard |
| `GET /api/teams` | Team rush vs. protection |
| `GET /api/games` | Games that have tracking data |
| `GET /api/plays?gameId=…` | Plays for a game |
| `GET /api/play?gameId=…&playId=…` | Frame-by-frame tracking for one play |
| `GET /api/player-search?q=…` | Player name search |

---

Built with Python standard library + vanilla JS.
