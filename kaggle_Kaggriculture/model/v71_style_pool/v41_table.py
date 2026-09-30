"""风格特化表:只用 V41/V43(+V43+B10)对手行,按商店组合选路线,seed 奇偶留出验证。"""
import json, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
r = json.load(open(HERE/'all_search.json'))
TARGET = {"V41", "V43", "V43+B10"}
per = collections.defaultdict(dict)
for opp, c, rid, sd, m in r:
    if m is not None and c and opp in TARGET: per[(opp, c, sd)][rid] = m
tr = {k: v for k, v in per.items() if k[2] % 2 == 0}; te = {k: v for k, v in per.items() if k[2] % 2 == 1}
d = collections.defaultdict(lambda: collections.defaultdict(list))
for (opp, c, sd), v in tr.items():
    for rid, m in v.items(): d[c][rid].append(m)
tab = {}
for c, v in d.items():
    cand = {rid: sum(ms)/len(ms) for rid, ms in v.items() if len(ms) >= 3}
    if len(cand) < 2 or -1 not in cand: continue
    b = max(cand.items(), key=lambda kv: kv[1])
    if b[0] != -1 and b[1] > cand[-1] + 500: tab[c] = b[0]   # 门槛:训练均值超基线 500
print(f"训练格 {len(tr)} 测试格 {len(te)};特化表 {len(tab)} 组合")
got = bs = 0; n = 0; w = bw = 0; byc = collections.defaultdict(lambda: [0, 0, 0, 0])
for (opp, c, sd), v in te.items():
    rid = tab.get(c)
    if rid is None or rid not in v or -1 not in v: continue
    got += v[rid]; bs += v[-1]; n += 1; w += v[rid] > 0; bw += v[-1] > 0
    x = byc[c]; x[0] += v[rid] - v[-1]; x[1] += 1; x[2] += v[rid] > 0; x[3] += v[-1] > 0
print(f"测试 {n} 局: 特化表 {w}/{n} 总{got:+.0f} | 基线 {bw}/{n} 总{bs:+.0f} | 净增 {got-bs:+.0f} 每局 {(got-bs)/max(1,n):+.0f}")
pos = {c: tab[c] for c, x in byc.items() if x[0] > 0}
print(f"测试为正的组合 {len(pos)}/{len(byc)}")
for c, x in sorted(byc.items(), key=lambda kv: -kv[1][0]):
    print(f"  {c:30s} 路线{tab[c]:4d} 净增{x[0]:+9.0f} 局{x[1]} 胜 {x[2]}/{x[3]}")
json.dump(tab, open(HERE/'v41_style_table.json', 'w'))
