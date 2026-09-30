"""分析分桶矩阵:①总胜率;②按对手行;③按首店桶;④(对手×首店) 两带互补性;⑤oracle 路由上界。"""
import json, sys, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in open(HERE / (sys.argv[1] if len(sys.argv) > 1 else "wm_famF_rb.jsonl"))]

cands = sorted({r["cand"] for r in rows})
# key: (cand, opp, first_shop) -> [win, n, margin_sum]
agg = collections.defaultdict(lambda: [0, 0, 0.0])
# 逐局配对: (opp, seed, seat) -> {cand: win}
paired = collections.defaultdict(dict)
for r in rows:
    w = 1 if r["my"] > r["their"] else (0.5 if r["my"] == r["their"] else 0)
    fs = r["first_shop"] or "?"
    for key in [(r["cand"], "ALL", "ALL"), (r["cand"], r["opp"], "ALL"),
                (r["cand"], "ALL", fs), (r["cand"], r["opp"], fs)]:
        a = agg[key]; a[0] += w; a[1] += 1; a[2] += r["my"] - r["their"]
    paired[(r["opp"], r["seed"], r["seat"])][r["cand"]] = w

print("=== 总口径 ===")
for c in cands:
    w, n, m = agg[(c, "ALL", "ALL")]
    print(f"{c:18s} {w:6.1f}/{n} = {w/n:.3f}  avg_margin={m/n:+8.0f}")

print("\n=== 按对手行(fam_F | rb | 差)===")
opps = sorted({r["opp"] for r in rows})
for o in opps:
    parts = []
    for c in cands:
        w, n, m = agg[(c, o, "ALL")]
        parts.append(f"{w:5.1f}/{n}")
    w0 = agg[(cands[0], o, "ALL")][0]; w1 = agg[(cands[1], o, "ALL")][0]
    print(f"{o:28s} {parts[0]} | {parts[1]}  diff={w1-w0:+.1f}")

print("\n=== 按首店桶 ===")
shops = sorted({r["first_shop"] or "?" for r in rows})
for s in shops:
    parts = []
    for c in cands:
        w, n, m = agg[(c, "ALL", s)]
        parts.append(f"{w:6.1f}/{n:3d}={w/max(n,1):.3f}")
    w0, n0, _ = agg[(cands[0], "ALL", s)]; w1, n1, _ = agg[(cands[1], "ALL", s)]
    print(f"{s:18s} {parts[0]} | {parts[1]}  diff={(w1/max(n1,1))-(w0/max(n0,1)):+.3f}")

print("\n=== (对手×首店) 桶中两带差(|diff|>=2 的桶)===")
for o in opps:
    for s in shops:
        k0, k1 = (cands[0], o, s), (cands[1], o, s)
        if agg[k0][1] == 0:
            continue
        w0, n, _ = agg[k0]; w1, _, _ = agg[k1]
        if abs(w1 - w0) >= 2:
            print(f"{o:28s} {s:18s} n={n:3d}  {cands[0].split('_')[0]}={w0:.1f} {cands[1].split('_')[0]}={w1:.1f} diff={w1-w0:+.1f}")

print("\n=== oracle 上界 ===")
tot = {c: 0.0 for c in cands}; oracle_shop = 0.0; oracle_full = 0.0; n_pairs = 0
# 按首店选带的可实现上界: 对每个 first_shop 桶取整体更优带
best_by_shop = {}
for s in shops:
    w0 = agg[(cands[0], "ALL", s)][0] / max(agg[(cands[0], "ALL", s)][1], 1)
    w1 = agg[(cands[1], "ALL", s)][0] / max(agg[(cands[1], "ALL", s)][1], 1)
    best_by_shop[s] = cands[1] if w1 > w0 else cands[0]
shop_router = 0.0
for r in rows:
    fs = r["first_shop"] or "?"
    if r["cand"] == best_by_shop[fs]:
        w = 1 if r["my"] > r["their"] else (0.5 if r["my"] == r["their"] else 0)
        shop_router += w
for key, d in paired.items():
    if len(d) != len(cands):
        continue
    n_pairs += 1
    for c in cands:
        tot[c] += d[c]
    oracle_full += max(d.values())
print(f"pairs={n_pairs}")
for c in cands:
    print(f"  {c:18s} {tot[c]/n_pairs:.3f}")
print(f"  oracle(逐局选优)   {oracle_full/n_pairs:.3f}")
print(f"  shop-router(按首店整体选优,可实现) {shop_router/n_pairs:.3f}")
print("  best_by_shop:", {s: b.split('_')[0] for s, b in best_by_shop.items()})
