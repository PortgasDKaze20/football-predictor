"""Step 3: form features. Every feature uses ONLY matches before kickoff."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
WINDOW = 5  # last 5 matches


def team_view(df):
    """One row per team per match (home and away both), so we can roll per team."""
    common = ["match_id", "league", "season", "Date"]
    h = df[common].assign(team=df.HomeTeam, gf=df.FTHG, ga=df.FTAG, sf=df.HS, sa=df.AS,
                          stf=df.HST, sta=df.AST, is_home=1)
    a = df[common].assign(team=df.AwayTeam, gf=df.FTAG, ga=df.FTHG, sf=df.AS, sa=df.HS,
                          stf=df.AST, sta=df.HST, is_home=0)
    t = pd.concat([h, a], ignore_index=True).sort_values(["team", "Date", "match_id"])
    t["pts"] = np.select([t.gf > t.ga, t.gf == t.ga], [3, 1], 0)
    return t


def add_rolling(t):
    g = t.groupby(["league", "team"], sort=False)
    stats = ["gf", "ga", "sf", "sa", "stf", "sta", "pts"]
    for s in stats:
        # shift(1) = exclude the current match -> no leakage
        t[f"{s}_l{WINDOW}"] = g[s].transform(lambda x: x.shift(1).rolling(WINDOW, min_periods=3).mean())
    t["rest_days"] = g["Date"].transform(lambda x: x.diff().dt.days).clip(upper=14)
    return t


def add_odds(df):
    """Bookmaker odds -> implied probabilities (pre-match, so no leakage).
    Uses market average odds, falling back to older average columns, then Bet365."""
    def num(col):
        s = pd.to_numeric(df[col], errors="coerce") if col in df else pd.Series(np.nan, index=df.index)
        return s.where(s > 1)  # valid decimal odds are > 1; anything else = missing

    for side in "HDA":
        df[f"odds_{side}"] = num(f"Avg{side}").fillna(num(f"BbAv{side}")).fillna(num(f"B365{side}"))
    inv = 1 / df[["odds_H", "odds_D", "odds_A"]]
    total = inv.sum(axis=1, min_count=3)  # > 1 because of the bookmaker margin; NaN if any odds missing
    for side in "HDA":
        df[f"p_book_{side}"] = inv[f"odds_{side}"] / total
    df["book_margin"] = total - 1
    return df


def build_features(df=None, save=True):
    if df is None:
        df = pd.read_csv(ROOT / "data" / "processed" / "matches_elo.csv", parse_dates=["Date"], low_memory=False)
    df["match_id"] = np.arange(len(df))
    t = add_rolling(team_view(df))
    feat_cols = [c for c in t.columns if c.endswith(f"_l{WINDOW}")] + ["rest_days"]
    home = t[t.is_home == 1][["match_id"] + feat_cols].add_prefix("h_").rename(columns={"h_match_id": "match_id"})
    away = t[t.is_home == 0][["match_id"] + feat_cols].add_prefix("a_").rename(columns={"a_match_id": "match_id"})
    out = df.merge(home, on="match_id").merge(away, on="match_id")
    for c in feat_cols:  # home-minus-away differences
        out[f"d_{c}"] = out[f"h_{c}"] - out[f"a_{c}"]
    out = add_odds(out)
    if save:
        out.to_csv(ROOT / "data" / "processed" / "matches_features.csv", index=False)
    return out


if __name__ == "__main__":
    out = build_features()
    print("saved", len(out), "matches,", out.filter(regex="^(h_|a_|d_)").shape[1], "feature columns")
    print("rows with missing form (team's first games):", out.filter(regex="^d_").isna().any(axis=1).sum())
