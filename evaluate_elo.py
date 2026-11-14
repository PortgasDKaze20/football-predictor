"""Step 2b: how good is Elo alone?

Train on 2016-17 .. 2023-24 (2015-16 is a warm-up season for the ratings),
test on 2024-25 and 2025-26, which the model never sees during training.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss

import elo

ROOT = Path(__file__).parent
CLASSES = ["A", "D", "H"]


def build(k, hfa):
    parts = [elo.run_elo(elo.load_league(lg), k=k, home_adv=hfa)[0] for lg in elo.LEAGUES]
    return pd.concat(parts, ignore_index=True)


def fit_eval(df, train_seasons, test_seasons):
    tr, te = df[df.season.isin(train_seasons)], df[df.season.isin(test_seasons)]
    model = LogisticRegression().fit(tr[["elo_diff"]] / 100, tr.FTR)
    p = model.predict_proba(te[["elo_diff"]] / 100)
    return te, p, model


# 1) tune K and home advantage on a validation season (2023-24) only
best = None
for k in [15, 20, 25, 30]:
    for hfa in [40, 60, 80]:
        df = build(k, hfa)
        _, p, _ = fit_eval(df, range(2016, 2023), [2023])
        ll = log_loss(df[df.season == 2023].FTR, p, labels=CLASSES)
        if best is None or ll < best[0]:
            best = (ll, k, hfa)
print(f"best on validation: K={best[1]} home_adv={best[2]} (log loss {best[0]:.4f})")

# 2) final test on 2024-25 + 2025-26
df = build(best[1], best[2])
te, p, model = fit_eval(df, range(2016, 2024), [2024, 2025])
pred = np.array(model.classes_)[p.argmax(1)]

base_p = np.tile(df[df.season.between(2016, 2023)].FTR.value_counts(normalize=True).reindex(CLASSES).values, (len(te), 1))
print(f"\nTEST SET: {len(te)} matches (2024-25 + 2025-26, all 5 leagues)")
print(f"  always pick home team : accuracy {(te.FTR == 'H').mean():.1%}  log loss {log_loss(te.FTR, base_p, labels=CLASSES):.4f}")
print(f"  Elo model             : accuracy {accuracy_score(te.FTR, pred):.1%}  log loss {log_loss(te.FTR, p, labels=CLASSES):.4f}")
print(f"  (draws predicted: {(pred == 'D').sum()})")

print("\nIf we only predict when the model is confident:")
conf = p.max(1)
for t in [0.5, 0.6, 0.7, 0.75]:
    m = conf >= t
    if m.sum():
        print(f"  top pick >= {t:.0%}: accuracy {(pred[m] == te.FTR.values[m]).mean():.1%} on {m.sum():4} matches ({m.mean():.0%} of games)")
