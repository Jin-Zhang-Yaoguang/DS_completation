"""录带 vs 反应式取证:跨局同步动作重合、开局前缀、按商店对分组的分歧点、与已知录带(V38 路由/带库)的重合。"""
import json, glob, collections, statistics as S
from pathlib import Path
MODEL = Path(__file__).resolve().parents[1]
G = [json.loads(l) for l in open("majkel_0910_12.jsonl")]
G = [g for g in G if g["date"] != "date=2026-09-10"]  # 09-10 仅 5 局,可能是旧版本
def key(a):
    units = [a.get("farmer") or []] + list(a.get("hands") or [])
    return json.dumps([units, sorted(map(json.dumps, a.get("market") or []))])
def ukey(a):
    return json.dumps([a.get("farmer") or []] + list(a.get("hands") or []))
def mkey(a):
    return json.dumps(sorted(map(json.dumps, a.get("market") or [])))
n = len(G); print("games", n)
# 1) 每步众数动作占比
for label, f in (("full", key), ("units", ukey), ("market", mkey)):
    row = []
    for t in (0, 1, 2, 5, 10, 24, 48, 71, 72, 100, 143, 144, 200, 288, 400, 500, 600, 648, 700, 717):
        c = collections.Counter(f(g["acts"][t]) for g in G if t < len(g["acts"]))
        row.append(f"t{t}:{c.most_common(1)[0][1]/n:.2f}")
    print(f"modal share [{label}]:", " ".join(row))
# 2) 与众数的相同前缀长度
modal = [collections.Counter(key(g["acts"][t]) for g in G if t < len(g["acts"])).most_common(1)[0][0] for t in range(719)]
pref = []
for g in G:
    k = 0
    while k < 719 and key(g["acts"][k]) == modal[k]: k += 1
    pref.append(k)
print("prefix-identical-to-modal: min", min(pref), "median", S.median(pref), "max", max(pref), "dist", collections.Counter(min(p // 24, 30) for p in pref).most_common(8))
# 3) 同商店对(第一次两个商店)内部两两分歧点
def shop_pair(g):
    for t, s in g["shops"]:
        if len(s) >= 2: return tuple(s[:2])
    return None
groups = collections.defaultdict(list)
for g in G: groups[shop_pair(g)].append(g)
div = []
for sp, gs in groups.items():
    for i in range(len(gs)):
        for j in range(i + 1, min(len(gs), i + 6)):
            a, b = gs[i]["acts"], gs[j]["acts"]; k = 0
            while k < 719 and key(a[k]) == key(b[k]): k += 1
            div.append(k)
print("pairwise first divergence (same shop pair): median", S.median(div), "quantiles", [sorted(div)[int(len(div) * q)] for q in (0.1, 0.25, 0.5, 0.75, 0.9)])
# 4) 与已知录带的步重合(单位动作完全相同的步占比)
tapes = {}
for f in glob.glob(str(MODEL / "v16_online_fidelity/tapes/*.json")) + glob.glob(str(MODEL / "opponent_pool_v1/tapes/*.json")) + glob.glob(str(MODEL / "v58_mosaic/*_family/*.json")) + glob.glob(str(MODEL / "v51_block_router/newpool/*.json")):
    try:
        d = json.load(open(f)); a = d["actions"] if isinstance(d, dict) else d
        if isinstance(a, list) and len(a) >= 700: tapes[Path(f).stem] = a
    except Exception: pass
for rid, a in json.load(open(MODEL / "v69_v38_knives/v38_routes.json")).items(): tapes[f"v38_route{rid}"] = a
print("reference tapes:", len(tapes))
best = collections.Counter(); scores = []
for g in G[:120]:
    sc = []
    for name, a in tapes.items():
        same = sum(1 for t in range(719) if t < len(a) and ukey(g["acts"][t]) == ukey(a[t]))
        sc.append((same / 719, name))
    sc.sort(reverse=True); scores.append(sc[0][0]); best[sc[0][1]] += 1
print("best tape overlap: median", round(S.median(scores), 3), "max", round(max(scores), 3), "top tapes", best.most_common(8))
# 5) 开局 72 步与录带重合
for name in [nm for _, nm in sorted(((sum(1 for t in range(72) if ukey(G[0]["acts"][t]) == ukey(a[t])), nm) for nm, a in tapes.items()), reverse=True)[:5]]:
    print("opening72 match", name, sum(1 for t in range(72) if ukey(G[0]["acts"][t]) == ukey(tapes[name][t])))
print("game0 first 6 steps:", [json.dumps(G[0]["acts"][t])[:160] for t in range(6)])
