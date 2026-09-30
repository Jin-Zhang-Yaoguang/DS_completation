"""y68j/y68i 线上战报与输局归因:家族、开局型、day1 帮工、商店组合、route、拉开时段。"""
import json, statistics
from pathlib import Path
from collections import Counter
S = Path(__file__).resolve().parent
RD = S / "live_replays3"
T = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity/tapes")
POOL = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1")
def sig(acts, a=0, b=144):
    return [json.dumps({"f": x.get("farmer"), "h": x.get("hands")}, sort_keys=True) for x in acts[a:b]]
ns = {}
exec((S / "kernels_0913" / "v38_main.py").read_text(), ns)
bases = {"v38": sig([a if isinstance(a, dict) else {} for a in ns["_ROUTES"][0][:144]]),
         "yhay": sig(json.load(open(T / "pub_yhay_0.json"))["actions"]),
         "t955": sig(json.load(open(T / "pub_t955_0.json"))["actions"]),
         "ult": sig(json.load(open(POOL / "tapes" / "ult_normal.json"))["actions"])}
def open_type(m):
    s = [(o[0], o[1] if len(o) > 1 else None, int(o[2]) if len(o) > 2 else None) for o in (m or []) if o]
    buys = sum(q for op, it, q in s if op == "BUY_PRODUCT" and it == "WHEAT")
    sells = sum(q for op, it, q in s if op == "SELL" and it == "WHEAT")
    return f"B{buys}/S{sells}"
ids = json.load(open(S / "ep_ids7.json"))
ALL = {}
for tag in ("y68j", "y68i"):
    rows = []
    for eid in ids[tag]:
        p = RD / f"episode-{eid}-replay.json"
        if not p.exists(): continue
        try: rep = json.load(open(p))
        except Exception: continue
        names = (rep.get("info") or {}).get("TeamNames") or []
        if "datatuu" not in names: continue
        rw = rep.get("rewards") or [0, 0]
        if names.count("datatuu") == 2:
            rows.append({"self": True, "m": abs((rw[0] or 0) - (rw[1] or 0))}); continue
        seat = names.index("datatuu"); o = 1 - seat
        steps = rep["steps"]
        my, op = rw[seat] or 0, rw[o] or 0
        oacts = [{"farmer": (steps[t][o].get("action") or {}).get("farmer") or ["PASS"],
                  "hands": (steps[t][o].get("action") or {}).get("hands") or []} for t in range(1, len(steps))]
        osig = sig(oacts)
        fam, ov = max(((n, sum(x == y for x, y in zip(osig, b)) / 144) for n, b in bases.items()), key=lambda kv: kv[1])
        try:
            town = steps[150][0]["observation"].get("town") or {}
            shops = tuple((town.get("unlocked_shops") or [])[:2])
        except Exception: shops = ()
        def hands_at(t, s):
            try: return len(steps[t][0]["observation"]["farms"][s].get("hands") or [])
            except Exception: return -1
        segs = []
        for t0 in range(144, 745, 144):
            tt = min(t0, len(steps) - 1)
            f = steps[tt][0]["observation"]["farms"]
            segs.append((f[seat].get("money") or 0) - (f[o].get("money") or 0))
        deltas = [segs[0]] + [segs[i] - segs[i-1] for i in range(1, len(segs))]
        worst_i = min(range(len(deltas)), key=lambda i: deltas[i])
        rows.append({"self": False, "ep": eid, "opp": str(names[o]), "my": my, "op": op, "m": my - op,
                     "fam": fam if ov >= 0.6 else "other", "ov": round(ov, 2),
                     "open_opp": open_type((steps[1][o].get("action") or {}).get("market")),
                     "d1h": hands_at(30, seat), "d1h_opp": hands_at(30, o),
                     "yarn": "YARN_STORE" in shops, "shops": "|".join(shops),
                     "worst": ["d0-6","d6-12","d12-18","d18-24","d24-30"][worst_i], "worst_d": int(deltas[worst_i])})
    ALL[tag] = rows
    real = [r for r in rows if not r["self"]]
    w = sum(r["m"] > 0 for r in real)
    print(f"\n=== {tag}: {len(real)} 局(内战 {len(rows)-len(real)}) {w}W{len(real)-w}L 胜率 {w/max(1,len(real)):.1%} ===")
    for key, lab in (("fam", "家族"), ("open_opp", "对手开局"), ("yarn", "有YARN")):
        agg = {}
        for r in real:
            a = agg.setdefault(r[key], [0, 0, []]); a[0] += 1; a[1] += r["m"] > 0; a[2].append(r["m"])
        print(f"  按{lab}: " + " | ".join(f"{k}:{v[1]}/{v[0]}({statistics.median(v[2]):+.0f})" for k, v in sorted(agg.items(), key=lambda kv: -kv[1][0])))
    print(f"  day1 我方帮工分布: {dict(Counter(r['d1h'] for r in real))}")
    losses = sorted((r for r in real if r["m"] <= 0), key=lambda r: r["m"])
    big = [r for r in losses if r["m"] < -10000]; mid = [r for r in losses if -10000 <= r["m"] < -3000]; thin = [r for r in losses if r["m"] >= -3000]
    print(f"  输局 {len(losses)}: 大崩(>10k) {len(big)} / 中(3-10k) {len(mid)} / 细刃(<3k) {len(thin)}")
    for r in losses:
        print(f"    {r['m']:+8.0f} vs {r['opp'][:20]:20s} {r['fam']:5s}({r['ov']}) 开局{r['open_opp']:9s} d1工{r['d1h']}v{r['d1h_opp']} {r['shops'][:28]:28s} 崩段{r['worst']}({r['worst_d']:+d})")
json.dump(ALL, open(S / "y68j_report.json", "w"), ensure_ascii=False)
