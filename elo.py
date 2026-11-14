"""Step 2: Elo ratings for every team, computed match by match in date order.

Each match gets the PRE-match ratings (home_elo, away_elo), so there is no
leakage: the rating only uses results from before kickoff.
"""
import glob
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
LEAGUES = ["premier-league", "la-liga", "bundesliga", "serie-a", "ligue-1"]

K = 15            # how fast ratings move after each match
HOME_ADV = 60     # Elo points added to the home team when computing expectations
REGRESS = 0.20    # at each new season, pull ratings 20% back toward the league mean
START = 1500


def load_all():
    """All 5 leagues from football-data.co.uk (results + stats + odds, incl. current season)."""
    df = pd.read_csv(ROOT / "data" / "raw" / "odds_top5.csv")
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, format="mixed")
    df["season"] = 2000 + df["season"].astype(int) // 100  # 1516 -> 2015 (= 2015-16)
    return df.dropna(subset=["FTHG", "FTAG"])  # played matches only


_ALL = None


def load_league(league):
    global _ALL
    if _ALL is None:
        _ALL = load_all()
    df = _ALL[_ALL.league == league].copy()
    return df.sort_values("Date", kind="stable").reset_index(drop=True)


def expected(r_home, r_away, home_adv=HOME_ADV):
    return 1 / (1 + 10 ** ((r_away - (r_home + home_adv)) / 400))


def goal_multiplier(gd):
    # bigger wins move ratings a bit more (World Football Elo style)
    gd = abs(gd)
    return 1 if gd <= 1 else (1.5 if gd == 2 else (11 + gd) / 8)


def run_elo(df, k=K, home_adv=HOME_ADV, regress=REGRESS):
    ratings, home_elo, away_elo = {}, [], []
    current_season, last_season_teams = None, set()
    for row in df.itertuples():
        if row.season != current_season:
            if ratings:
                mean = sum(ratings.values()) / len(ratings)
                ratings = {t: r + regress * (mean - r) for t, r in ratings.items()}
                # promoted teams start at the average of last season's bottom 3
                bottom3 = sorted(ratings[t] for t in last_season_teams)[:3]
                promoted_start = sum(bottom3) / len(bottom3)
            else:
                promoted_start = START
            season_teams = set(df.loc[df.season == row.season, "HomeTeam"])
            for t in season_teams:
                if t not in last_season_teams:
                    ratings[t] = promoted_start
            last_season_teams, current_season = season_teams, row.season

        rh, ra = ratings.setdefault(row.HomeTeam, promoted_start), ratings.setdefault(row.AwayTeam, promoted_start)
        home_elo.append(rh)
        away_elo.append(ra)
        if pd.isna(row.FTHG):  # upcoming fixture: record pre-match ratings, no update
            continue
        result = 1.0 if row.FTHG > row.FTAG else (0.5 if row.FTHG == row.FTAG else 0.0)
        change = k * goal_multiplier(row.FTHG - row.FTAG) * (result - expected(rh, ra, home_adv))
        ratings[row.HomeTeam] = rh + change
        ratings[row.AwayTeam] = ra - change

    out = df.copy()
    out["home_elo"], out["away_elo"] = home_elo, away_elo
    out["elo_diff"] = out["home_elo"] + home_adv - out["away_elo"]
    return out, ratings


if __name__ == "__main__":
    all_matches, final = [], {}
    for lg in LEAGUES:
        m, r = run_elo(load_league(lg))
        all_matches.append(m)
        final[lg] = r
    matches = pd.concat(all_matches, ignore_index=True)
    matches.to_csv(ROOT / "data" / "processed" / "matches_elo.csv", index=False)
    print("saved", len(matches), "matches")
    for lg, r in final.items():
        top = sorted(r.items(), key=lambda x: -x[1])[:3]
        print(f"{lg:15}", ", ".join(f"{t} {v:.0f}" for t, v in top))
