"""合并全部矩阵,求:①各候选总胜率与行剖面;②嫁接可用集合内的最优 shop 路由表;
③该路由表的可实现胜率与 oracle 上界。"""
import json, collections, itertools
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = []
for fn in ["wm_famF_rb.jsonl", "wm_more.jsonl"]:
    rows += [json.loads(l) for l in open(HERE / fn)]

GRAFTABLE = ["fam_F_new", "rb_7925cb146f", "cand_0_ec979a", "famF_var_621efa65ad", "rb_var_8830803d1a"]
ALLC = sorted({r["cand"] for r in rows})
opps = sorted({r["opp"] for r in rows})
shops = sorted({r["first_shop"] or "?" for r in rows})

W = collections.defaultdict(lambda: [0.0, 0])   # (cand, opp, shop) -> [win, n]
for r in rows:
    w = 1 if r["my"] > r["their"] else (0.5 if r["my"] == r["their"] else 0)
    fs = r["first_shop"] or "?"
    for key in [(r["cand"], "ALL", "ALL"), (r["cand"], r["opp"], "ALL"), (r["cand"], "ALL", fs), (r["cand"], r["opp"], fs)]:
        W[key][0] += w; W[key][1] += 1

print("=== 各候选总胜率 ===")
for c in ALLC:
    w, n = W[(c, "ALL", "ALL")]
    tag = " (graftable)" if c in GRAFTABLE else " (异构,参考)"
    print(f"{c:28s} {w:7.1f}/{n} = {w/n:.3f}{tag}")

print("\n=== 行剖面(候选 × 对手,胜率%)===")
hdr = "opp".ljust(28) + "".join(c[:10].rjust(11) for c in ALLC)
print(hdr)
for o in opps:
    line = o.ljust(28)
    for c in ALLC:
        w, n = W[(c, o, "ALL")]
        line += f"{100*w/max(n,1):10.0f}%"
    print(line)

# 最优 shop 路由表(只用 graftable):每个 shop 桶取桶内总胜率最高的带
best = {}
for s in shops:
    scores = [(W[(c, "ALL", s)][0] / max(W[(c, "ALL", s)][1], 1), c) for c in GRAFTABLE]
    best[s] = max(scores)[1]
print("\n=== graftable 最优路由表 ===")
for s in shops:
    print(f"  {s:18s} -> {best[s]}  ({100*W[(best[s],'ALL',s)][0]/max(W[(best[s],'ALL',s)][1],1):.1f}%)")

# 路由表可实现胜率(用对应带在该桶的实测局面)
num = den = 0.0
for r in rows:
    fs = r["first_shop"] or "?"
    if r["cand"] == best[fs]:
        num += 1 if r["my"] > r["their"] else (0.5 if r["my"] == r["their"] else 0)
        den += 1
print(f"\nshop-router 可实现: {num/den:.3f} (n={int(den)})")

# oracle(graftable 逐局选优)
paired = collections.defaultdict(dict)
for r in rows:
    if r["cand"] in GRAFTABLE:
        w = 1 if r["my"] > r["their"] else (0.5 if r["my"] == r["their"] else 0)
        paired[(r["opp"], r["seed"], r["seat"])][r["cand"]] = w
oracle = sum(max(d.values()) for d in paired.values() if len(d) == len(GRAFTABLE))
np_ = sum(1 for d in paired.values() if len(d) == len(GRAFTABLE))
print(f"oracle(graftable 逐局): {oracle/np_:.3f} (n={np_})")

# (opp,shop) 粒度 oracle: 若路由特征还能看到对手信息的理论上界
os_best = 0.0; os_n = 0
for o in opps:
    for s in shops:
        cands_ws = [(W[(c, o, s)][0], W[(c, o, s)][1], c) for c in GRAFTABLE if W[(c, o, s)][1] > 0]
        if cands_ws:
            w, n, c = max(cands_ws)
            os_best += w; os_n += n
print(f"oracle(对手×首店 桶选优): {os_best/os_n:.3f}")
