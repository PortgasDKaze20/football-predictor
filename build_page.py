"""Build predictions/index.html: a phone-friendly page with today's picks + track record."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
PRED = ROOT / "predictions"
LEAGUE_NAMES = {"premier-league": "Premier League", "la-liga": "La Liga", "bundesliga": "Bundesliga",
                "serie-a": "Serie A", "ligue-1": "Ligue 1"}


def track_record():
    res = pd.read_csv(ROOT / "data" / "raw" / "odds_top5.csv", low_memory=False).dropna(subset=["FTR"])
    res = res[["HomeTeam", "AwayTeam", "FTR", "FTHG", "FTAG", "season"]]
    res = res[res.season == res.season.max()]
    rows = []
    files = [(f, False) for f in sorted(PRED.glob("20*.csv"))] + [(f, True) for f in sorted((PRED / "test").glob("*.csv"))]
    seen = set()
    for f, is_test in files:
        p = pd.read_csv(f).merge(res, on=["HomeTeam", "AwayTeam"], how="inner")
        for r in p.itertuples():
            key = (r.HomeTeam, r.AwayTeam)
            if key in seen:  # a match can appear in several daily files; keep the first prediction
                continue
            seen.add(key)
            rows.append({"kickoff": r.kickoff_myt, "league": LEAGUE_NAMES.get(r.league, r.league),
                         "home": r.HomeTeam, "away": r.AwayTeam, "pick": r.pick,
                         "confidence": round(float(r.confidence), 3), "result": r.FTR,
                         "score": f"{int(r.FTHG)}-{int(r.FTAG)}", "correct": bool(r.pick == r.FTR), "test": is_test})
    return rows


def main():
    latest = json.loads((PRED / "latest.json").read_text())
    for m in latest["matches"]:
        m["league"] = LEAGUE_NAMES.get(m["league"], m["league"])
    data = {"latest": latest, "record": track_record()}
    html = TEMPLATE.replace("__DATA__", json.dumps(data))
    (PRED / "index.html").write_text(html)
    print("built predictions/index.html:", len(latest["matches"]), "upcoming,", len(data["record"]), "settled")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Football Predictions</title>
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Predictions">
<meta name="theme-color" content="#0d1117">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  :root{--bg:#0d1117;--card:#161b22;--line:#262d37;--text:#e6edf3;--muted:#8b949e;--home:#3fb950;--draw:#8b949e;--away:#58a6ff;--gold:#e3b341;--bad:#f85149}
  @media (prefers-color-scheme: light){:root{--bg:#f6f8fa;--card:#fff;--line:#e3e8ee;--text:#1f2328;--muted:#656d76;--home:#1a7f37;--draw:#8c959f;--away:#0969da;--gold:#9a6700;--bad:#cf222e}}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
  main{max-width:640px;margin:0 auto;padding:20px 16px 48px}
  header h1{font-size:22px;margin:0 0 4px;letter-spacing:-.01em}
  .meta{color:var(--muted);font-size:13px}
  h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:28px 0 10px;font-weight:600}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:10px}
  .card.top{border-color:var(--gold)}
  .row1{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--muted);margin-bottom:6px}
  .badge{font-size:11px;font-weight:600;padding:2px 8px;border-radius:99px;border:1px solid currentColor}
  .badge.top{color:var(--gold)} .badge.good{color:var(--home)}
  .teams{font-weight:600;font-size:16px;display:flex;justify-content:space-between;gap:8px}
  .teams span:last-child{text-align:right}
  .bar{display:flex;height:8px;border-radius:99px;overflow:hidden;margin:10px 0 6px;background:var(--line)}
  .bar i{display:block}
  .pcts{display:flex;justify-content:space-between;font:500 12px 'JetBrains Mono',monospace;color:var(--muted)}
  .pcts b{color:var(--text)}
  .pick{margin-top:8px;font-size:14px}
  .pick strong{font-weight:600}
  .empty{color:var(--muted);text-align:center;padding:24px 14px}
  details summary{cursor:pointer;color:var(--muted);font-size:14px;padding:6px 0;list-style:none}
  details summary::before{content:"▸ "} details[open] summary::before{content:"▾ "}
  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
  .stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;text-align:center}
  .stat .n{font:600 20px 'JetBrains Mono',monospace}
  .stat .l{font-size:11px;color:var(--muted);margin-top:2px}
  .rec{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:14px}
  .rec .ok{width:22px;text-align:center;font-weight:700}
  .rec .ok.y{color:var(--home)} .rec .ok.n{color:var(--bad)}
  .rec .m{flex:1;min-width:0} .rec .m div:last-child{color:var(--muted);font-size:12px}
  .rec .c{font:500 12px 'JetBrains Mono',monospace;color:var(--muted);text-align:right}
  .tag{font-size:10px;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:0 4px;margin-left:4px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  td,th{padding:7px 4px;border-bottom:1px solid var(--line);text-align:left}
  th{color:var(--muted);font-weight:500} td:not(:first-child),th:not(:first-child){text-align:right;font-family:'JetBrains Mono',monospace}
  .legend{display:flex;gap:14px;font-size:12px;color:var(--muted);margin-top:6px}
  .legend i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:4px}
  footer{margin-top:32px;color:var(--muted);font-size:12px}
</style>
</head>
<body>
<main>
  <header>
    <h1>⚽ Football Predictions</h1>
    <div class="meta" id="meta"></div>
    <div class="legend"><span><i style="background:var(--home)"></i>Home</span><span><i style="background:var(--draw)"></i>Draw</span><span><i style="background:var(--away)"></i>Away</span></div>
  </header>

  <h2>Upcoming</h2>
  <div id="upcoming"></div>

  <h2>Track record</h2>
  <div class="stats" id="stats"></div>
  <div id="record" style="margin-top:8px"></div>

  <h2>How reliable is this?</h2>
  <div class="card">
    <table>
      <tr><th>Confidence</th><th>Correct</th><th>Share of games</th></tr>
      <tr><td>⭐ 80%+</td><td>90%</td><td>3%</td></tr>
      <tr><td>75%+</td><td>83%</td><td>8%</td></tr>
      <tr><td>✅ 70%+</td><td>77%</td><td>15%</td></tr>
      <tr><td>60%+</td><td>70%</td><td>32%</td></tr>
      <tr><td>All matches</td><td>54%</td><td>100%</td></tr>
    </table>
    <div class="meta" style="margin-top:8px">Tested on 3,483 matches from 2024-25 and 2025-26 that the model never saw. Model: Elo ratings + last-5 form + bookmaker odds, top 5 European leagues.</div>
  </div>

  <footer>Statistical predictions, not betting advice. The model is about as accurate as bookmakers, not better. Checks for new fixtures every 3 hours.</footer>
</main>
<script>
const DATA = __DATA__;
const NAMES = {H: "Home win", D: "Draw", A: "Away win"};
const pct = x => Math.round(x * 100) + "%";
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const L = DATA.latest;
document.getElementById("meta").textContent = `Updated ${L.generated} MYT · results to ${L.results_to}`;

function card(m) {
  const top = m.confidence >= 0.8, good = m.confidence >= 0.7;
  const badge = top ? '<span class="badge top">⭐ Top pick</span>' : good ? '<span class="badge good">✅ Good pick</span>' : "";
  const pickTeam = m.pick === "H" ? m.home : m.pick === "A" ? m.away : "";
  return `<div class="card ${top ? "top" : ""}">
    <div class="row1"><span>${esc(m.league)} · ${esc(m.kickoff)}</span>${badge}</div>
    <div class="teams"><span>${esc(m.home)}</span><span>${esc(m.away)}</span></div>
    <div class="bar"><i style="width:${m.p_home*100}%;background:var(--home)"></i><i style="width:${m.p_draw*100}%;background:var(--draw)"></i><i style="width:${m.p_away*100}%;background:var(--away)"></i></div>
    <div class="pcts"><span><b>${pct(m.p_home)}</b> home</span><span><b>${pct(m.p_draw)}</b> draw</span><span>away <b>${pct(m.p_away)}</b></span></div>
    <div class="pick">Pick: <strong>${NAMES[m.pick]}${pickTeam ? " — " + esc(pickTeam) : ""}</strong> (${pct(m.confidence)})</div>
  </div>`;
}

const up = document.getElementById("upcoming");
if (!L.matches.length) {
  up.innerHTML = `<div class="card empty">No top-5 league matches with odds in the next ${L.days_ahead} days.<br><span style="font-size:13px">During international breaks, or before the bookmakers publish odds, this stays empty.</span></div>`;
} else {
  const strong = L.matches.filter(m => m.confidence >= 0.7).sort((a, b) => b.confidence - a.confidence);
  const rest = L.matches.filter(m => m.confidence < 0.7);
  let h = strong.length ? strong.map(card).join("") : '<div class="card empty">No ⭐ or ✅ picks this time — all matches are close calls.</div>';
  if (rest.length) h += `<details><summary>Other matches (${rest.length}) — close calls</summary>${rest.map(card).join("")}</details>`;
  up.innerHTML = h;
}

const R = DATA.record;
const live = R.filter(r => !r.test);
const rate = (arr, t) => { const s = arr.filter(r => r.confidence >= t); return s.length ? `${s.filter(r => r.correct).length}/${s.length}` : "–"; };
const base = live.length ? live : R;
document.getElementById("stats").innerHTML = [["⭐ 80%+", 0.8], ["✅ 70%+", 0.7], ["All", 0]].map(([l, t]) =>
  `<div class="stat"><div class="n">${rate(base, t)}</div><div class="l">${l} correct</div></div>`).join("");
const recEl = document.getElementById("record");
if (!R.length) recEl.innerHTML = '<div class="meta">Fills in once predicted matches are played.</div>';
else {
  const note = live.length ? "" : '<div class="meta" style="margin-bottom:4px">No live picks settled yet. Showing the test run on Nov 7–9 (predicted using only pre-match data).</div>';
  const shown = (live.length ? live : R).filter(r => r.confidence >= 0.7).slice(-30).reverse();
  recEl.innerHTML = note + (shown.length ? shown.map(r => `<div class="rec">
      <div class="ok ${r.correct ? "y" : "n"}">${r.correct ? "✓" : "✗"}</div>
      <div class="m"><div>${esc(r.home)} ${esc(r.score)} ${esc(r.away)}${r.test ? '<span class="tag">test</span>' : ""}</div><div>${esc(r.league)} · picked ${NAMES[r.pick]}</div></div>
      <div class="c">${pct(r.confidence)}</div></div>`).join("") : '<div class="meta">No 70%+ picks settled yet.</div>');
}
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
