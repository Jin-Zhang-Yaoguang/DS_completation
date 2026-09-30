"""线上 replay 盘点:含 FARMERS_MARKET 组合的对局,按组合/版本统计胜负,列输局。"""
import json, statistics
from pathlib import Path
from collections import defaultdict
S = Path(__file__).resolve().parent
tagmap = {}
for f in ("ep_ids7.json", "ep_ids8.json", "ep_ids9.json"):
    p = S / f
    if p.exists():
        for tag, v in json.load(open(p)).items():
            for e in v: tagmap.setdefault(e, tag)
rows = []
for p in (S / "live_replays3").glob("episode-*-replay.json"):
    eid = int(p.name.split("-")[1])
    try: rep = json.load(open(p))
    except Exception: continue
    nm = rep["info"]["TeamNames"]
    if nm.count("datatuu") != 1 or len(rep["steps"]) < 700: continue
    seat = nm.index("datatuu"); o = 1 - seat; st = rep["steps"]
    shops = ((st[150][0]["observation"].get("town") or {}).get("unlocked_shops") or [])[:2]
    if "FARMERS_MARKET" not in shops: continue
    m1 = [x for x in (st[1][o].get("action") or {}).get("market") or [] if x]
    op_open = (tuple(int(x[2]) for x in m1 if x[0] == "BUY_PRODUCT" and len(x) > 2), tuple(int(x[2]) for x in m1 if x[0] == "SELL" and len(x) > 2))
    rows.append(dict(ep=eid, tag=tagmap.get(eid, "旧"), opp=str(nm[o]), combo="|".join(shops), m=rep["rewards"][seat] - rep["rewards"][o], op_open=op_open, seed=rep["info"]["seed"]))
json.dump(rows, open(S / "fm_live_rows.json", "w"), ensure_ascii=False)
print(f"含 FM 组合的线上对局 {len(rows)} 局:胜 {sum(r['m']>0 for r in rows)} 负 {sum(r['m']<=0 for r in rows)}")
by = defaultdict(list)
for r in rows: by[r["combo"]].append(r)
print(f"\n{'组合':34s} {'局':>3s} {'胜':>3s} {'中位':>7s}  版本分布")
for c, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    vers = defaultdict(lambda: [0, 0])
    for r in v: vers[r["tag"]][0] += 1; vers[r["tag"]][1] += r["m"] > 0
    print(f"{c:34s} {len(v):3d} {sum(r['m']>0 for r in v):3d} {statistics.median([r['m'] for r in v]):+7.0f}  " + " ".join(f"{t}:{w}/{n}" for t, (n, w) in sorted(vers.items())))
print("\n输局明细:")
for r in sorted(rows, key=lambda r: r["m"]):
    if r["m"] > 0: break
    print(f"  {r['m']:+8.0f} {r['tag']:6s} vs {r['opp'][:18]:18s} {r['combo']:32s} 对手开局{r['op_open']}")
