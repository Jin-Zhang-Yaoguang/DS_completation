"""线上 B15/S60 开局对手里 V41(旧 route0)vs V42/V43(新带)占比:非 YARN 局对手 t145-300 动作分别对齐 route0 与 V42 表新带。"""
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
ct = {}
for sid in ("56248994", "56238337", "56234249", "56231344"):
    p = S / f"eps_{sid}.json"
    if p.exists():
        raw = p.read_text()
        if "[" in raw:
            for e in json.loads(raw[raw.index('['):raw.rindex(']') + 1]): ct[e["id"]] = e["createTime"][:13]
res = []
for p in (S / "live_replays3").glob("episode-*-replay.json"):
    eid = int(p.name.split("-")[1])
    try: rep = json.load(open(p))
    except Exception: continue
    nm = rep["info"]["TeamNames"]
    if nm.count("datatuu") != 1 or len(rep["steps"]) < 400: continue
    o = 1 - nm.index("datatuu"); st = rep["steps"]
    m1 = [x for x in (st[1][o].get("action") or {}).get("market") or [] if x]
    if (tuple(int(x[2]) for x in m1 if x[0] == "BUY_PRODUCT" and len(x) > 2), tuple(int(x[2]) for x in m1 if x[0] == "SELL" and len(x) > 2)) != ((5, 10), (60,)): continue
    shops = tuple(((st[150][0]["observation"].get("town") or {}).get("unlocked_shops") or [])[:2])
    if "YARN_STORE" in shops or shops not in tab: continue
    nt = new_routes[tab[shops]]
    ov_new = statistics.mean(key(st[t + 1][o].get("action")) == key(nt[t] if isinstance(nt[t], dict) else {}) for t in range(145, 300))
    ov_old = statistics.mean(key(st[t + 1][o].get("action")) == key(r0[t]) for t in range(145, 300))
    res.append((ct.get(eid, "早期"), "V42/V43新带" if ov_new > ov_old else "V41旧带", eid))
print(f"非 YARN 局的 B15/S60 对手共 {len(res)} 局:", dict(Counter(r[1] for r in res)))
by_day = {}
for t, fam, _ in res:
    d = t[:10] if t != "早期" else "早期"
    by_day.setdefault(d, Counter())[fam] += 1
for d in sorted(by_day): print(f"   {d}: {dict(by_day[d])}")
