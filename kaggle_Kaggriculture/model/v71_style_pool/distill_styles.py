"""风格池 v1:7 天官方数据按开局签名聚类 → 风格草表(局数≥20 或队伍≥2),关联金牌家族知识。"""
import json, glob, csv, collections, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
lb = {r['TeamName']: (int(r['Rank']), float(r['Score'])) for r in csv.DictReader(open(HERE/'lb.csv', encoding='utf-8-sig'))}
rows = []
for f in sorted(glob.glob(str(HERE/'sig_*.jsonl'))):
    date = f.split('sig_')[1][:10]
    for l in open(f):
        r = json.loads(l)
        if 'err' in r: continue
        r['date'] = date; rows.append(r)
# 已知家族(金牌研究)
FAMILY = {"Majkel1337": "Majkel家族", "DSM": "Majkel家族", "Orbital Terraformer": "Majkel家族",
          "Artem The Farmer 🍅": "t955前缀族", "Unknown Mother-Goose": "t955前缀族", "现实是个乐子": "t955前缀族",
          "Mengfei Li": "t955前缀族", "feel the agi": "t955前缀族", "AI是我的豆包": "t955前缀族",
          "leave you": "fork大簇", "Catalyst": "fork大簇", "local": "fork大簇", "lumen": "fork大簇",
          "carbonapi": "fork大簇", "Cow Boy": "fork大簇", "アルモンド": "fork大簇", "fog flower": "fork大簇",
          "nilochan": "fork大簇", "yjshyfy": "fork大簇",
          "SpaTaro": "独立:SpaTaro", "THIRD FARM CLUB": "独立:THIRD", "Sida Zuo": "独立:SidaZuo",
          "ymg_aq": "独立:ymg_aq", "HowardLeeTW": "独立:Howard", "Excluding": "独立:Excluding",
          "Otter Vibe": "独立:Otter", "Ebi": "独立:Ebi", "M & M & P & Q": "独立:MMPQ"}
by = collections.defaultdict(list)
for r in rows: by[r['op_sig']].append(r)
styles = []
for sig, v in by.items():
    teams = collections.Counter(r['team'] for r in v)
    if len(v) < 20 and len(teams) < 2: continue
    fams = collections.Counter(FAMILY.get(t, "?") for t in teams)
    w = sum(1 for r in v if r['margin'] > 0)
    top = [(t, lb.get(t, (9999, 0))) for t, _ in teams.most_common(4)]
    styles.append(dict(sig=sig, n=len(v), teams=len(teams), win=round(w/len(v), 2),
                       med=round(st.median(r['margin'] for r in v)),
                       fam=fams.most_common(1)[0][0], top=[f"{t}(#{rk})" for t, (rk, sc) in top],
                       days=sorted({r['date'][-2:] for r in v}), open0=v[0]['open'][0]))
styles.sort(key=lambda s: -s['n'])
json.dump(styles, open(HERE/'style_pool_v1.json', 'w'), ensure_ascii=False, indent=1)
cov = sum(s['n'] for s in styles)
print(f"总 {len(rows)} 座位局;风格 {len(styles)} 个,覆盖 {cov}({cov/len(rows):.0%})")
print(f"{'签名':9s}{'局':>5s}{'队':>3s}{'胜率':>5s}{'中位':>7s}  家族 / 代表 / 活跃日")
for s in styles[:30]:
    print(f"{s['sig']:9s}{s['n']:5d}{s['teams']:3d}{s['win']:5.0%}{s['med']:7d}  {s['fam']:12s} {', '.join(s['top'][:2]):46s} {','.join(s['days'])}")
fam_agg = collections.defaultdict(int)
for s in styles: fam_agg[s['fam']] += s['n']
print("按家族覆盖:", dict(sorted(fam_agg.items(), key=lambda kv: -kv[1])))
