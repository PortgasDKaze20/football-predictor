"""Step B: daily predictions.

1. Merge the newest refreshed files (fp_results_*.csv, fp_fixtures_*.csv) into data/raw
2. Rebuild Elo + form + odds features with upcoming fixtures included
3. Train the model on every finished match since 2016-17
4. Predict upcoming fixtures and save predictions/YYYY-MM-DD.csv + predictions/latest.md
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import elo
import features

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "predictions"
MYT, UK = ZoneInfo("Asia/Kuala_Lumpur"), ZoneInfo("Europe/London")
DAYS_AHEAD = 3
TOP_PICK, GOOD_PICK = 0.80, 0.70
NAMES = {"H": "Home win", "D": "Draw", "A": "Away win"}


def newest(pattern):
    files = sorted(RAW.glob(pattern))
    return files[-1] if files else None


def load_inputs():
    hist = pd.read_csv(RAW / "odds_top5.csv")
    ref = newest("fp_refresh_*.csv")
    fx = pd.DataFrame(columns=hist.columns)
    if ref is not None:
        fresh = pd.read_csv(ref)
        res = fresh[fresh.kind == "result"].drop(columns="kind")
        fx = fresh[fresh.kind == "fixture"].drop(columns="kind")
        if len(res):  # replace this season's rows with the fresh copy
            hist = pd.concat([hist[hist.season != res.season.iloc[0]], res], ignore_index=True)
            hist.to_csv(RAW / "odds_top5.csv", index=False)
    return hist, fx, ref, ref


def write_json(now, played, up=None):
    import json
    matches = []
    if up is not None:
        for r in up.itertuples():
            matches.append({"kickoff": r.kickoff_myt, "date": r.Date.strftime("%Y-%m-%d"), "league": r.league,
                            "home": r.HomeTeam, "away": r.AwayTeam, "p_home": round(r.p_home, 3),
                            "p_draw": round(r.p_draw, 3), "p_away": round(r.p_away, 3), "pick": r.pick,
                            "confidence": round(r.confidence, 3)})
    (OUT / "latest.json").write_text(json.dumps({
        "generated": now.strftime("%Y-%m-%d %H:%M"), "results_to": played.Date.max().strftime("%d %b %Y"),
        "days_ahead": DAYS_AHEAD, "matches": matches}, indent=1))


def kickoff_myt(date, time):
    t = time if isinstance(time, str) and ":" in time else "15:00"
    uk = datetime.strptime(f"{date.date()} {t}", "%Y-%m-%d %H:%M").replace(tzinfo=UK)
    return uk.astimezone(MYT)


def main():
    hist, fx, cur, fx_file = load_inputs()
    import os
    now = datetime.fromisoformat(os.environ["FP_NOW"]).replace(tzinfo=MYT) if os.environ.get("FP_NOW") else datetime.now(MYT)

    for df in (hist, fx):
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, format="mixed")
        df["season"] = 2000 + df["season"].astype(int) // 100
    played = hist.dropna(subset=["FTHG", "FTAG"])
    fx = fx.copy()
    for c in ["FTHG", "FTAG", "FTR"]:
        fx[c] = np.nan
    fx["kickoff_myt"] = [kickoff_myt(d, t) for d, t in zip(fx.Date, fx.Time)]
    fx = fx[(fx.kickoff_myt > now) & (fx.kickoff_myt < now + timedelta(days=DAYS_AHEAD))]

    # Elo per league with fixtures appended (fixtures get pre-match ratings, no update)
    parts = []
    for lg in elo.LEAGUES:
        both = pd.concat([played[played.league == lg], fx[fx.league == lg].drop(columns="kickoff_myt")],
                         ignore_index=True).sort_values("Date", kind="stable").reset_index(drop=True)
        parts.append(elo.run_elo(both)[0])
    df = features.build_features(pd.concat(parts, ignore_index=True), save=False)
    df["is_fixture"] = df.FTR.isna()
    df = pd.get_dummies(df, columns=["league"], prefix="lg", dtype=float)
    for lg in elo.LEAGUES:
        df[f"lg_{lg}"] = df.get(f"lg_{lg}", 0.0)

    cols = (["elo_diff"] + [c for c in df.columns if c.startswith("d_")] + ["h_rest_days", "a_rest_days"]
            + [f"lg_{lg}" for lg in elo.LEAGUES] + ["p_book_H", "p_book_D", "p_book_A"])
    train = df[(~df.is_fixture) & (df.season >= 2016)].dropna(subset=cols)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, C=0.1)).fit(train[cols], train.FTR)

    OUT.mkdir(exist_ok=True)
    today = now.strftime("%Y-%m-%d")
    lines = [f"# Football predictions — {today}", "",
             f"Generated {now:%Y-%m-%d %H:%M} MYT. Data: results to {played.Date.max():%d %b %Y}"
             f" ({cur.name if cur is not None else 'no refresh file'}). Trained on {len(train):,} matches.", ""]

    up = df[df.is_fixture].dropna(subset=cols)
    skipped = int(df.is_fixture.sum()) - len(up)
    if up.empty:
        lines += [f"No top-5 league matches with odds in the next {DAYS_AHEAD} days."]
        if skipped:
            lines += [f"({skipped} fixtures skipped: missing odds or not enough form data yet.)"]
        (OUT / "latest.md").write_text("\n".join(lines) + "\n")
        write_json(now, played)
        print("\n".join(lines))
        return

    p = model.predict_proba(up[cols])
    cls = list(model.classes_)
    up = up.assign(p_home=p[:, cls.index("H")], p_draw=p[:, cls.index("D")], p_away=p[:, cls.index("A")])
    up["pick"] = up[["p_away", "p_draw", "p_home"]].values.argmax(1)
    up["pick"] = up.pick.map({0: "A", 1: "D", 2: "H"})
    up["confidence"] = up[["p_home", "p_draw", "p_away"]].max(axis=1)
    up["league"] = up[[f"lg_{lg}" for lg in elo.LEAGUES]].values.argmax(1)
    up["league"] = up.league.map(dict(enumerate(elo.LEAGUES)))
    up["kickoff_myt"] = [kickoff_myt(d, t).strftime("%a %d %b %H:%M") for d, t in zip(up.Date, up.Time)]
    up = up.sort_values(["Date", "Time"])

    keep = ["kickoff_myt", "league", "HomeTeam", "AwayTeam", "p_home", "p_draw", "p_away", "pick", "confidence",
            "home_elo", "away_elo", "odds_H", "odds_D", "odds_A"]
    up[keep].round(3).to_csv(OUT / f"{today}.csv", index=False)
    write_json(now, played, up)

    def row(r):
        star = "⭐ " if r.confidence >= TOP_PICK else ("✅ " if r.confidence >= GOOD_PICK else "")
        return (f"| {star}{r.kickoff_myt} | {r.league} | {r.HomeTeam} vs {r.AwayTeam} | "
                f"{r.p_home:.0%} / {r.p_draw:.0%} / {r.p_away:.0%} | {NAMES[r.pick]} ({r.confidence:.0%}) |")

    top = up[up.confidence >= TOP_PICK]
    lines += ["## ⭐ Top picks (80%+ confidence — historically ~85-90% correct)", ""]
    lines += (["| Kickoff (MYT) | League | Match | Home / Draw / Away | Pick |", "|---|---|---|---|---|"]
              + [row(r) for r in top.itertuples()]) if len(top) else ["None today."]
    lines += ["", "## All matches (✅ = 70%+, historically ~77% correct)", "",
              "| Kickoff (MYT) | League | Match | Home / Draw / Away | Pick |", "|---|---|---|---|---|"]
    lines += [row(r) for r in up.itertuples()]
    if skipped:
        lines += ["", f"({skipped} fixtures skipped: missing odds or not enough form data yet.)"]
    (OUT / "latest.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
