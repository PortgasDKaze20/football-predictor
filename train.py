"""Step 3b: train models on Elo + form, compare on the same unseen test seasons."""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).parent
CLASSES = ["A", "D", "H"]

df = pd.read_csv(ROOT / "data" / "processed" / "matches_features.csv", parse_dates=["Date"], low_memory=False)
df = pd.get_dummies(df, columns=["league"], prefix="lg", dtype=float)

ELO = ["elo_diff"]
FORM = [c for c in df.columns if c.startswith("d_")] + ["h_rest_days", "a_rest_days"]
LEAGUE = [c for c in df.columns if c.startswith("lg_")]
ODDS = ["p_book_H", "p_book_D", "p_book_A"]

train = df[df.season.between(2016, 2023)].dropna(subset=ELO + FORM + ODDS)
test = df[df.season.isin([2024, 2025])].dropna(subset=ELO + FORM + ODDS)

models = {
    "Elo only (logistic)": (make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)), ELO),
    "Elo + form (logistic)": (make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, C=0.1)), ELO + FORM + LEAGUE),
    "Odds only (logistic)": (make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)), ODDS),
    "Elo + form + odds (logistic)": (make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, C=0.1)), ELO + FORM + LEAGUE + ODDS),
}

print(f"train {len(train)} matches (2016-17..2023-24) | test {len(test)} matches (2024-25 + 2025-26)\n")
results = {}
for name, (m, cols) in models.items():
    m.fit(train[cols], train.FTR)
    p = m.predict_proba(test[cols])
    pred = np.array(m.classes_)[p.argmax(1)]
    results[name] = (p, pred)
    print(f"{name:32} accuracy {accuracy_score(test.FTR, pred):.1%}   log loss {log_loss(test.FTR, p, labels=CLASSES):.4f}")

bp = test[["p_book_A", "p_book_D", "p_book_H"]].values
bpred = np.array(CLASSES)[bp.argmax(1)]
print(f"{'Bookmakers themselves':32} accuracy {accuracy_score(test.FTR, bpred):.1%}   log loss {log_loss(test.FTR, bp, labels=CLASSES):.4f}")

best = "Elo + form + odds (logistic)"  # main model: uses everything; ~equal to odds-only
p, pred = results[best]
print(f"\nBest: {best}. Confidence buckets:")
conf = p.max(1)
for t in [0.5, 0.6, 0.7, 0.75, 0.8]:
    m = conf >= t
    if m.sum() >= 20:
        print(f"  top pick >= {t:.0%}: accuracy {(pred[m] == test.FTR.values[m]).mean():.1%} on {m.sum():4} matches ({m.mean():.0%} of games)")
