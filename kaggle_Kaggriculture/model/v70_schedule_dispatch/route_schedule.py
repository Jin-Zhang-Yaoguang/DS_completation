"""阶段1:逐条强制路线跑一局(seed 固定),抽出 雇工/非卖出买单/田间布局事件(含格子),写 schedule_routes.json。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE / "proto"))
FIELD = {"PLANT", "BUILD_PASTURE", "BUILD_COOP", "PLACE", "DIG"}
def one(job):
    rid, seed = job
    os.environ["KAG_FORCE_ROUTE"] = str(rid)
    import sched_proto as sp
    seat = 0; o = 1
    me = sp.fidelity.make_agent(f"sub:{sp.S}/y68fr_main.py"); op = sp.fidelity.make_agent(f"sub:{sp.S}/y68s2_main.py")
    k = sp.engine.load_kagsim(); g = k.Game(seed=seed); t = 0
    hires = collections.Counter(); buys = []; field = []
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [me(obs[0]), op(obs[1])]
        f = obs[0]["farms"][0]; us = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        for x in (a[0].get("market") or []):
            if not x: continue
            if x[0] == "HIRE": hires[t] += 1
            elif x[0] != "SELL": buys.append([t] + list(x))
        for i, c in enumerate(([a[0].get("farmer") or ["PASS"]] + list(a[0].get("hands") or []))[:len(us)]):
            if c and c[0] in FIELD: field.append([t, us[i][0], us[i][1]] + list(c))
        g.step(a[0], a[1]); t += 1
    return rid, seed, dict(hires=hires, buys=buys, field=field, bank=float(g.reward(0)))
if __name__ == "__main__":
    ns = {}; exec(open(HERE / "agents" / "y68x3b13_main.py").read(), ns)
    rids = sorted(ns["_IMPL"].chassis.routes)
    jobs = [(r, s) for r in rids for s in (3001, 3002)]
    with ProcessPoolExecutor(7) as ex: R = list(ex.map(one, jobs, chunksize=2))
    out = collections.defaultdict(dict)
    for rid, seed, d in R: out[str(rid)][str(seed)] = d
    json.dump(out, open(HERE / "schedule_routes_raw.json", "w"))
    # 同路线两 seed 一致性(144 步后)
    same = {}
    for rid in rids:
        a, b = out[str(rid)]["3001"], out[str(rid)]["3002"]
        f = lambda d: (tuple((int(t), c) for t, c in sorted(d["hires"].items()) if int(t) >= 144), tuple(tuple(x) for x in d["buys"] if x[0] >= 144), tuple(tuple(x) for x in d["field"] if x[0] >= 144))
        fa, fb = f(a), f(b)
        same[rid] = tuple(int(x == y) for x, y in zip(fa, fb))
    print("路线数", len(rids), "两 seed 在 t≥144 完全一致(雇工,买单,布局):", collections.Counter(same.values()).most_common())
