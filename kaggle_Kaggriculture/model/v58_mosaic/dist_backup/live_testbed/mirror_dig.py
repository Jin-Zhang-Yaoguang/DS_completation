"""①同带镜像 vs 非镜像胜率;②镜像输局首分叉:谁偏离带、偏离成什么。"""
import json, statistics
from pathlib import Path
S = Path(__file__).resolve().parent
RD = S / "live_replays3"
pack = json.load(open(S / "v42_router_pack.json"))
tab = {tuple(k.split("|")): v for k, v in pack["shop_routes"].items()}
new_routes = {int(k): v for k, v in pack["routes"].items()}
ns = {}; exec((S / "kernels_0913" / "v38_main.py").read_text(), ns)
v38r = ns["_ROUTES"]; router = ns["_router"]
BL = {("BAKERY", "FARMERS_MARKET"), ("PIZZA_SHOP", "PIZZA_SHOP")}
ids = json.load(open(S / "ep_ids7.json"))
def key(a): return json.dumps({"f": (a or {}).get("farmer"), "h": (a or {}).get("hands")}, sort_keys=True)
cls = {}
detail = []
for tag in ("y68j", "y68i"):
    for eid in ids[tag]:
        p = RD / f"episode-{eid}-replay.json"
        if not p.exists(): continue
        rep = json.load(open(p)); names = rep["info"]["TeamNames"]
        if names.count("datatuu") != 1: continue
        seat = names.index("datatuu"); o = 1 - seat; steps = rep["steps"]
        m1 = (steps[1][o].get("action") or {}).get("market") or []
        bq = sum(int(x[2]) for x in m1 if x and x[0] == "BUY_PRODUCT" and len(x) > 2)
        sq = sum(int(x[2]) for x in m1 if x and x[0] == "SELL" and len(x) > 2)
        rw = rep["rewards"]; m = (rw[seat] or 0) - (rw[o] or 0)
        shops = tuple(((steps[150][0]["observation"].get("town") or {}).get("unlocked_shops") or [])[:2])
        yarn = "YARN_STORE" in shops
        # 我方实际所用带
        if (not yarn) and tag == "y68j" and shops not in BL and shops in tab:
            my_tape = new_routes[tab[shops]]
        else:
            my_tape = v38r[router({"town": {"unlocked_shops": list(shops)}}, 144, {})]
        ov_me = statistics.mean(key(steps[t+1][seat].get("action")) == key(my_tape[t] if isinstance(my_tape[t], dict) else {}) for t in range(145, 360))
        ov_op = statistics.mean(key(steps[t+1][o].get("action")) == key(my_tape[t] if isinstance(my_tape[t], dict) else {}) for t in range(145, 360))
        mirror = ov_op >= 0.95
        opener = "B15S60" if (bq, sq) == (15, 60) else ("B43S30" if (bq, sq) == (43, 30) else "other")
        k2 = (tag, "镜像" if mirror else "非镜像", opener)
        cls.setdefault(k2, []).append(m)
        if mirror and m < 0:
            fd = next((t for t in range(2, len(steps)) if key(steps[t][seat].get("action")) != key(steps[t][o].get("action"))), None)
            if fd:
                ti = fd - 1
                tp = my_tape[ti] if ti < len(my_tape) and isinstance(my_tape[ti], dict) else {}
                a_me = steps[fd][seat].get("action") or {}; a_op = steps[fd][o].get("action") or {}
                me_dev = key(a_me) != key(tp); op_dev = key(a_op) != key(tp)
                # 找出不同的单元
                um = [a_me.get("farmer")] + list(a_me.get("hands") or []); uo = [a_op.get("farmer")] + list(a_op.get("hands") or []); ut = [tp.get("farmer")] + list(tp.get("hands") or [])
                diffs = [(i, um[i] if i < len(um) else None, uo[i] if i < len(uo) else None, ut[i] if i < len(ut) else None) for i in range(max(len(um), len(uo))) if (um[i] if i < len(um) else None) != (uo[i] if i < len(uo) else None)]
                detail.append((tag, m, str(names[o])[:14], "Y" if yarn else "N", fd, "我偏" if me_dev else "", "彼偏" if op_dev else "", diffs[:3],
                               (steps[fd-1][seat].get("action") or {}).get("market"), (steps[fd-1][o].get("action") or {}).get("market")))
print("① 胜率分组(胜/局 中位margin):")
for k2 in sorted(cls):
    v = cls[k2]
    print(f"  {k2[0]} {k2[1]:4s} 对手开局{k2[2]:6s}: {sum(x>0 for x in v)}/{len(v)} ({sum(x>0 for x in v)/len(v):.0%}) 中位 {statistics.median(v):+.0f}")
print("\n② 镜像输局首分叉(单元号, 我, 彼, 带):")
for d in sorted(detail, key=lambda d: d[1]):
    print(f"  {d[0]} {d[1]:+6.0f} {d[2]:14s} {d[3]} t{d[4]} {d[5]}{d[6]} {d[7]}")
    print(f"        前一步 market 我={d[8]} 彼={d[9]}")
