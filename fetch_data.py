"""Download all data straight from football-data.co.uk (used by GitHub Actions).

Writes:
  data/raw/odds_top5.csv             all seasons 2015-16 .. current, results + stats + odds
  data/raw/fp_refresh_YYYYMMDD.csv   upcoming top-5 fixtures with pre-match odds (kind=fixture)
Same formats as the browser refresh, so predict.py works unchanged.
"""
import csv
import io
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
BASE = "https://www.football-data.co.uk"
DIVS = {"E0": "premier-league", "SP1": "la-liga", "D1": "bundesliga", "I1": "serie-a", "F1": "ligue-1"}
KEEP = ["Date", "Time", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "HS", "AS", "HST", "AST",
        "B365H", "B365D", "B365A", "PSH", "PSD", "PSA", "AvgH", "AvgD", "AvgA", "BbAvH", "BbAvD", "BbAvA"]


def current_season_start(now):
    return now.year if now.month >= 7 else now.year - 1


def get_rows(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "football-predictor/1.0"})
            text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8-sig", errors="replace")
            return [r for r in csv.DictReader(io.StringIO(text)) if r.get("HomeTeam")]
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                raise
            print("retry", url, e)
            time.sleep(5)


def main():
    now = datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
    RAW.mkdir(parents=True, exist_ok=True)
    last = current_season_start(now)
    seasons = [f"{y % 100:02d}{(y + 1) % 100:02d}" for y in range(2015, last + 1)]

    with open(RAW / "odds_top5.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["league", "season"] + KEEP)
        for div, league in DIVS.items():
            for s in seasons:
                try:
                    rows = get_rows(f"{BASE}/mmz4281/{s}/{div}.csv")
                except Exception as e:  # noqa: BLE001
                    print("FAIL", div, s, e)
                    continue
                for r in rows:
                    w.writerow([league, s] + [r.get(k, "") or "" for k in KEEP])
                print(div, s, len(rows))

    cur = seasons[-1]
    fixtures = [r for r in get_rows(f"{BASE}/fixtures.csv") if r.get("Div") in DIVS]
    with open(RAW / f"fp_refresh_{now:%Y%m%d}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kind", "league", "season"] + KEEP)
        for r in fixtures:
            w.writerow(["fixture", DIVS[r["Div"]], cur] + [r.get(k, "") or "" for k in KEEP])
    print("fixtures (top 5):", len(fixtures))


if __name__ == "__main__":
    main()
