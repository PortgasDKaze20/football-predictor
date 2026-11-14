"""Step 1: download match data for the top 5 European leagues."""
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/datasets/football-datasets/main/datasets"
LEAGUES = ["premier-league", "la-liga", "bundesliga", "serie-a", "ligue-1"]
SEASONS = [f"{y % 100:02d}{(y + 1) % 100:02d}" for y in range(2015, 2026)]  # 1516 .. 2526

out = Path(__file__).parent / "data" / "raw"
for league in LEAGUES:
    (out / league).mkdir(parents=True, exist_ok=True)
    for s in SEASONS:
        dest = out / league / f"season-{s}.csv"
        try:
            urllib.request.urlretrieve(f"{BASE}/{league}/season-{s}.csv", dest)
            print("ok  ", league, s)
        except Exception as e:
            print("FAIL", league, s, e)
