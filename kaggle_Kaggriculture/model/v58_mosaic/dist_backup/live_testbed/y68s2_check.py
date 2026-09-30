"""y68s2 上线排查:①线上我方开局/路由是否符合设计;②分组胜率;③输局明细;同窗口对比 y68r2。"""
import json, statistics
from pathlib import Path
from collections import Counter
S = Path(__file__).resolve().parent
RD = S / "live_replays3"
pack = json.load(open(S / "v42_router_pack.json"))
tab = {tuple(k.split("|")): v for k, v in pack["shop_routes"].items()}
new_routes = {int(k): v for k, v in pack["routes"].items()}
ns = {}; exec((S / "kernels_0913" / "v38_main.py").read_text(), ns)
v38r = ns["_ROUTES"]; router = ns["_router"]
BL = {("BAKERY","SMOOTHIE_SHOP"),("BRUNCH_SPOT","FARMERS_MARKET"),("FARMERS_MARKET","FARMERS_MARKET"),("ICE_CREAM_SHOP","PIZZA_SHOP"),
      ("PET_CAFE","FARMERS_MARKET"),("PIZZA_SHOP","ICE_CREAM_SHOP"),("PIZZA_SHOP","SMOOTHIE_SHOP"),("BAKERY","FARMERS_MARKET"),("PIZZA_SHOP","PIZZA_SHOP")}
def key(a): return json.dumps({"f": (a or {}).get("farmer"), "h": (a or {}).get("hands")}, sort_keys=True)
def opener(m):
    m = [x for x in (m or []) if x]
    return (tuple(int(x[2]) for x in m if x[0] == "BUY_PRODUCT" and len(x) > 2), tuple(int(x[2]) for x in m if x[0] == "SELL" and len(x) > 2))
ids = json.load(open(S / "ep_ids9.json"))
ct = {}
for sid in ("56248994", "56238337"):
    raw = open(S / f"eps_{sid}.json").read()
    for e in json.loads(raw[raw.index('['):raw.rindex(']') + 1]): ct[e["id"]] = e["createTime"]
s2_start = min(ct[e] for e in ids["y68s2"]) if ids["y68s2"] else "9"
rows = {"y68s2": [], "y68r2": []}
for tag in ("y68s2", "y68r2"):
    for eid in ids[tag]:
        p = RD / f"episode-{eid}-replay.json"
        if not p.exists(): continue
        rep = json.load(open(p)); nm = rep["info"]["TeamNames"]
        if nm.count("datatuu") != 1: continue
        seat = nm.index("datatuu"); o = 1 - seat; st = rep["steps"]
        my_open = opener((st[1][seat].get("action") or {}).get("market"))
        op_open = opener((st[1][o].get("action") or {}).get("market"))
        shops = tuple(((st[150][0]["observation"].get("town") or {}).get("unlocked_shops") or [])[:2])
        yarn = "YARN_STORE" in shops
        ov_new = ov_old = None
        if not yarn and shops in tab:
            nt = new_routes[tab[shops]]
            ov_new = statistics.mean(key(st[t+1][seat].get("action")) == key(nt[t] if isinstance(nt[t], dict) else {}) for t in range(145, 300))
        ot = v38r[router({"town": {"unlocked_shops": list(shops)}}, 144, {})]
        ov_old = statistics.mean(key(st[t+1][seat].get("action")) == key(ot[t]) for t in range(145, 300))
        m = rep["rewards"][seat] - rep["rewards"][o]
        def hands(t, s):
            try: return len(st[t][0]["observation"]["farms"][s].get("hands") or [])
            except Exception: return -1
        rows[tag].append(dict(ep=eid, opp=str(nm[o]), m=m, my_open=my_open, op_open=op_open, shops="|".join(shops), yarn=yarn,
                              bl=shops in BL, ov_new=ov_new, ov_old=ov_old, d1=(hands(30, seat), hands(30, o)), late=ct.get(eid, "") >= s2_start))
def wr(v): return f"{sum(r['m']>0 for r in v)}/{len(v)} ({sum(r['m']>0 for r in v)/max(1,len(v)):.0%}) 中位{statistics.median([r['m'] for r in v]) if v else 0:+.0f}"
print("① 线上行为核对(y68s2)")
print("   我方 t1 开局分布:", dict(Counter(r["my_open"] for r in rows["y68s2"])))
nb = [r for r in rows["y68s2"] if not r["yarn"]]
bad_route = [r for r in nb if (r["bl"] and (r["ov_new"] or 0) > r["ov_old"]) or ((not r["bl"]) and r["ov_new"] is not None and r["ov_new"] < r["ov_old"])]
print(f"   非YARN局 {len(nb)},路由与设计不符 {len(bad_route)}: " + ", ".join(f"{r['shops']} bl={r['bl']} new{r['ov_new']:.2f}/old{r['ov_old']:.2f}" for r in bad_route[:6]))
print(f"   day1 帮工(我,彼)分布: {dict(Counter(r['d1'] for r in rows['y68s2']))}")
print("\n② 胜率")
print(f"   y68s2 全部: {wr(rows['y68s2'])}")
print(f"   y68r2 全部: {wr(rows['y68r2'])} | 同窗口(y68s2 上线后): {wr([r for r in rows['y68r2'] if r['late']])}")
for tag in ("y68s2", "y68r2"):
    v = rows[tag] if tag == "y68s2" else [r for r in rows[tag] if r["late"]]
    g = {}
    for r in v:
        op = r["op_open"]
        k = {((5, 10), (60,)): "V41/42/43", ((13, 30), (30,)): "V38原版", ((10, 0), (10,)): "B10", ((10,), (5,)): "B10"}.get(op, "其他")
        g.setdefault(("对手开局", k), []).append(r)
        g.setdefault(("组合", "YARN" if r["yarn"] else ("黑名单" if r["bl"] else "新带")), []).append(r)
    print(f"   {tag}{'(同窗口)' if tag=='y68r2' else ''}: " + " | ".join(f"{a}:{b} {wr(x)}" for (a, b), x in sorted(g.items())))
print("\n③ y68s2 输局")
for r in sorted(rows["y68s2"], key=lambda r: r["m"]):
    if r["m"] > 0: break
    print(f"   {r['m']:+8.0f} vs {r['opp'][:18]:18s} 对手开局{str(r['op_open']):22s} {r['shops'][:30]:30s} bl={int(r['bl'])} d1帮工{r['d1']} 新带重合{r['ov_new'] if r['ov_new'] is None else round(r['ov_new'],2)} 旧带{r['ov_old']:.2f}")
json.dump(rows, open(S / "y68s2_check.json", "w"), ensure_ascii=False)
