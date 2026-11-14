// Daily refresh, run by Claude inside the built-in browser on https://www.football-data.co.uk
// Downloads ONE file to ~/Downloads: fp_refresh_YYYYMMDD.csv
//   kind=result  -> current-season results + stats + odds (top 5 leagues)
//   kind=fixture -> upcoming fixtures + pre-match odds (top 5 leagues)
const SEASON = '2627';
const divs = {E0:'premier-league', SP1:'la-liga', D1:'bundesliga', I1:'serie-a', F1:'ligue-1'};
const keep = ['Date','Time','HomeTeam','AwayTeam','FTHG','FTAG','FTR','HS','AS','HST','AST','B365H','B365D','B365A','PSH','PSD','PSA','AvgH','AvgD','AvgA','BbAvH','BbAvD','BbAvA'];
const stamp = new Date().toLocaleDateString('sv-SE').replace(/-/g,'');  // local date
const parse = t => t.replace(/^﻿/,'').split(/\r?\n/).filter(l => l.trim() && !/^,+$/.test(l));
const pick = (head, cols, keepCols) => keepCols.map(k => { const i = head.indexOf(k); return i >= 0 ? (cols[i] ?? '') : ''; });
function save(name, text) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], {type: 'text/csv'}));
  a.download = name; document.body.appendChild(a); a.click(); a.remove();
}
const res = ['kind,league,season,' + keep.join(',')], report = [];
for (const [d, lg] of Object.entries(divs)) {
  const L = parse(await (await fetch(`/mmz4281/${SEASON}/${d}.csv?t=${Date.now()}`)).text());
  const head = L[0].split(',');
  let n = 0;
  for (const l of L.slice(1)) { const c = l.split(','); if (c[head.indexOf('HomeTeam')]) { res.push(['result', lg, SEASON, ...pick(head, c, keep)].join(',')); n++; } }
  report.push(`${d}:${n}`);
}
const F = parse(await (await fetch(`/fixtures.csv?t=${Date.now()}`)).text());
const fhead = F[0].split(',');
let nfx = 0;
for (const l of F.slice(1)) { const c = l.split(','); const lg = divs[c[0]]; if (lg) { res.push(['fixture', lg, SEASON, ...pick(fhead, c, keep)].join(',')); nfx++; } }
save(`fp_refresh_${stamp}.csv`, res.join('\n'));
({results: report.join(' '), fixtures_top5: nfx, stamp})
