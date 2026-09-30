"""交叉筛选:同一组合在(A)全对手测试集与(B)V41/V43 特化测试集都为正,且推荐同一路线 → 进入增补表。"""
import json, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
r = json.load(open(HERE/'all_search.json'))
def build(target=None):
    per = collections.defaultdict(dict)
    for opp, c, rid, sd, m in r:
        if m is None or not c: continue
        if target and opp not in target: continue
        per[(opp, c, sd)][rid] = m
    tr = {k: v for k, v in per.items() if k[2] % 2 == 0}; te = {k: v for k, v in per.items() if k[2] % 2 == 1}
    d = collections.defaultdict(lambda: collections.defaultdict(list))
    for (opp, c, sd), v in tr.items():
        for rid, m in v.items(): d[c][rid].append(m)
    tab = {}
    for c, v in d.items():
        cand = {rid: sum(ms)/len(ms) for rid, ms in v.items() if len(ms) >= 3}
        if len(cand) < 2 or -1 not in cand: continue
        b = max(cand.items(), key=lambda kv: kv[1])
        if b[0] != -1 and b[1] > cand[-1]: tab[c] = b[0]
    res = collections.defaultdict(lambda: [0, 0, 0])
    for (opp, c, sd), v in te.items():
        rid = tab.get(c)
        if rid is None or rid not in v or -1 not in v: continue
        x = res[c]; x[0] += v[rid] - v[-1]; x[1] += 1; x[2] = rid
    return {c: (x[2], x[0], x[1]) for c, x in res.items()}
A = build(None); B = build({"V41", "V43", "V43+B10"})
WK = {"BRUNCH_SPOT|BAKERY": 112, "FARMERS_MARKET|BAKERY": 103, "YARN_STORE|PIZZA_SHOP": 126,
      "YARN_STORE|SMOOTHIE_SHOP": 126, "FARMERS_MARKET|YARN_STORE": 126}
print(f"{'组合':30s}{'A路线':>5s}{'A净增':>9s}{'A局':>4s} |{'B路线':>5s}{'B净增':>9s}{'B局':>4s}  判定")
add = {}
for c in sorted(set(A) | set(B)):
    a = A.get(c); b = B.get(c)
    if not a or not b: continue
    both_pos = a[1] > 0 and b[1] > 0; same = a[0] == b[0]
    verdict = ""
    if c in WK: verdict = "已在wk表"
    elif both_pos and same and a[2] + b[2] >= 12: verdict = "★新增"; add[c] = a[0]
    elif both_pos and same: verdict = "样本不足"
    print(f"{c:30s}{a[0]:5d}{a[1]:+9.0f}{a[2]:4d} |{b[0]:5d}{b[1]:+9.0f}{b[2]:4d}  {verdict}")
print("\n增补表:", json.dumps(add))
json.dump(add, open(HERE/'wk2_add_table.json', 'w'))
