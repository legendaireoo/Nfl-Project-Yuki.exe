"""Download the NFL Big Data Bowl regional-event data (games, plays, players, PFF scouting, tracking).

Usage:  python download_data.py [max_games]
Files land in ./data and ./data/tracking. Already-downloaded files are skipped.
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

BASE = "https://raw.githubusercontent.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data/main/data"
DATA_DIR = Path(__file__).parent / "data"


def fetch(rel_path: str) -> str:
    out = DATA_DIR / rel_path
    if out.exists() and out.stat().st_size > 0:
        return f"skip {rel_path}"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part")
    try:
        with requests.get(f"{BASE}/{rel_path}", stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
        tmp.replace(out)
        return f"ok   {rel_path}"
    except Exception as exc:  # network errors should not kill the whole batch
        tmp.unlink(missing_ok=True)
        return f"FAIL {rel_path}: {exc}"


def main() -> None:
    for f in ["games.csv", "plays.csv", "players.csv", "pffScoutingData.csv"]:
        print(fetch(f), flush=True)
    games = pd.read_csv(DATA_DIR / "games.csv").sort_values("gameId")
    ids = games.gameId.tolist()
    if len(sys.argv) > 1:
        ids = ids[: int(sys.argv[1])]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for msg in pool.map(lambda g: fetch(f"tracking/tracking_{g}.csv"), ids):
            print(msg, flush=True)


if __name__ == "__main__":
    main()
