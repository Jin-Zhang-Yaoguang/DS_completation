"""线上 13+13/13 与 13+13/26 等"中买型"开局对手:非 YARN 局 t145-300 动作对齐 route0 vs V42 新带;并统计出现次数与我方胜负。"""
import json, statistics
from pathlib import Path
from collections import Counter
S = Path(__file__).resolve().parent
pack = json.load(open(S / "v42_router_pack.json"))
tab = {tuple(k.split("|")): v for k, v in pack["shop_routes"].items()}
new_routes = {int(k): v for k, v in pack["routes"].items()}
ns = {}; exec((S / "kernels_0913" / "v38_main.py").read_text(), ns)
r0 = ns["_ROUTES"][0]
def key(a): return json.dumps({"f": (a or {}).get("farmer"), "h": (a or {}).get("hands")}, sort_keys=True)
rows = []
for p in (S / "live_replays3").glob("episode-*-replay.json"):
    try: rep = json.load(open(p))
    except Exception: continue
    nm = rep["info"]["TeamNames"]
    if nm.count("datatuu") != 1 or len(rep["steps"]) < 400: continue
    seat = nm.index("datatuu"); o = 1 - seat; st = rep["steps"]
    m1 = [x for x in (st[1][o].get("action") or {}).get("market") or [] if x]
    op_open = (tuple(int(x[2]) for x in m1 if x[0] == "BUY_PRODUCT" and len(x) > 2), tuple(int(x[2]) for x in m1 if x[0] == "SELL" and len(x) > 2))
    if op_open not in (((13, 13), (13,)), ((13, 13), (26,))): continue
    shops = tuple(((st[150][0]["observation"].get("town") or {}).get("unlocked_shops") or [])[:2])
    fam = "YARN局不可判"
    ov_old = statistics.mean(key(st[t + 1][o].get("action")) == key(r0[t]) for t in range(145, 300))
    if "YARN_STORE" not in shops and shops in tab:
        nt = new_routes[tab[shops]]
        ov_new = statistics.mean(key(st[t + 1][o].get("action")) == key(nt[t] if isinstance(nt[t], dict) else {}) for t in range(145, 300))
        fam = "新带(V42/43系)" if ov_new > max(ov_old, 0.5) else ("旧route0(V38/41系)" if ov_old > 0.5 else f"其他(新{ov_new:.2f}/旧{ov_old:.2f})")
    m = rep["rewards"][seat] - rep["rewards"][o]
    rows.append((op_open, str(nm[o]), "|".join(shops), fam, m))
print(f"线上 13+13 开局对手 {len(rows)} 局,我方胜 {sum(r[4]>0 for r in rows)}")
print("家族分布:", dict(Counter(r[3] for r in rows)))
print("对手名分布:", dict(Counter(r[1] for r in rows).most_common(8)))
for r in sorted(rows, key=lambda r: r[4])[:12]:
    print(f"   {r[4]:+7.0f} vs {r[1][:16]:16s} 开局{r[0]} {r[2]:30s} {r[3]}")
