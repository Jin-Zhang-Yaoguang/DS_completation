import json, collections, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
r = json.load(open(HERE/'t300_search.json'))
per = collections.defaultdict(dict); c3map = {}
for opp, sh, rid, sd, m in r:
    if m is None or not sh: continue
    key = (opp, "|".join(sh[:2]), sd)
    per[key][rid] = m; c3map[key] = sh[2] if len(sh) > 2 else "?"
print("有效格", len(per))
# 口径1:组合级(忽略第3店)——t300 是否有优于不切的固定选择
d = collections.defaultdict(lambda: collections.defaultdict(list))
for (opp, c2, sd), v in per.items():
    for rid, m in v.items(): d[c2][rid].append(m - v.get(-1, 0))
print("\n口径1 组合级(相对不切的均值增益,局数):")
for c2, v in sorted(d.items()):
    row = sorted(((sum(ms)/len(ms), rid, len(ms)) for rid, ms in v.items() if rid != -1), reverse=True)
    best = row[0]
    print(f"  {c2:30s} 最优 t300->{best[1]} 均增 {best[0]:+8.0f}(n={best[2]})  次优 {row[1][1]}:{row[1][0]:+.0f}")
# 口径2:组合×第3店
d2 = collections.defaultdict(lambda: collections.defaultdict(list))
for key, v in per.items():
    opp, c2, sd = key; c3 = c3map[key]
    for rid, m in v.items(): d2[(c2, c3)][rid].append(m - v.get(-1, 0))
print("\n口径2 (组合, 第3店) 中 n>=4 且最优增益>2000 的格:")
cnt_pos = 0
for (c2, c3), v in sorted(d2.items()):
    row = sorted(((sum(ms)/len(ms), rid, len(ms)) for rid, ms in v.items() if rid != -1), reverse=True)
    best = row[0]
    if best[2] >= 4 and best[0] > 2000:
        cnt_pos += 1
        print(f"  {c2:28s}+{c3:16s} t300->{best[1]} 均增 {best[0]:+8.0f}(n={best[2]})")
print("显著格数", cnt_pos, "/", len(d2))
# 胜负口径:切换后翻盘/翻车统计(全体)
flip = collections.Counter()
for key, v in per.items():
    b = v.get(-1)
    if b is None: continue
    for rid, m in v.items():
        if rid == -1: continue
        flip[("win+" if (m > 0 and b <= 0) else "win-" if (m <= 0 and b > 0) else "same")] += 1
print("胜负变化(所有候选切换 vs 不切):", dict(flip))
