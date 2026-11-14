# Football Predictor

Daily home/draw/away predictions for the Premier League, La Liga, Bundesliga, Serie A and Ligue 1.

**Model:** Elo ratings + last-5-match form (goals, shots, shots on target, rest days) + bookmaker odds,
logistic regression trained on every match since 2016-17.

**Tested on 3,483 unseen matches (2024-25, 2025-26):**

| Confidence | Correct | Share of games |
|---|---|---|
| 80%+ | 90% | 3% |
| 70%+ | 77% | 15% |
| All | 54% | 100% |

## How it runs

GitHub Actions (`.github/workflows/daily.yml`) runs every day at 9:33am Malaysia time:
`fetch_data.py` → `predict.py` → `build_page.py` → GitHub Pages. Prediction files are committed
to `predictions/` so the page can show a track record.

Run it manually from the **Actions** tab → *Daily predictions* → *Run workflow*.

Data: [football-data.co.uk](https://www.football-data.co.uk). Statistical predictions, not betting advice.
