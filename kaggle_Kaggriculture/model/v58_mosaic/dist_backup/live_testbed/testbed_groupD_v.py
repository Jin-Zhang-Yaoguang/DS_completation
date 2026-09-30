"""测试床 D 组:对手 V38 原版开局(买13+30/卖30)的线上局,线上 seed+席位,反应式 V38 对手;y68v vs op_b30。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
def norm(a):
    a = a or {}
    return json.dumps({"f": a.get("farmer") or ["PASS"], "h": a.get("hands") or [], "m": a.get("market") or []}, sort_keys=True)
def one(job):
    eid, ver = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    rep = json.load(open(S / f"live_replays3/episode-{eid}-replay.json"))
    nm = rep["info"]["TeamNames"]; seat = nm.index("datatuu"); o = 1 - seat; st = rep["steps"]
    live_op = [st[t + 1][o].get("action") or {} for t in range(len(st) - 1)]
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py"); op = fidelity.make_agent(f"sub:{S}/kernels_0913/v38_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=rep["info"]["seed"]); t = 0; mis = 0; h30 = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[o] = op(obs[o])
        if t < 144 and t < len(live_op) and norm(acts[o]) != norm(live_op[t]): mis += 1
        g.step(acts[0], acts[1]); t += 1
        if t == 30:
            f = g.observe(0)["farms"]; h30 = (len(f[seat].get("hands") or []), len(f[o].get("hands") or []))
    return eid, str(nm[o]), ver, mis, h30, g.reward(seat) - g.reward(o), rep["rewards"][seat] - rep["rewards"][o]
if __name__ == "__main__":
    ids = json.load(open(S / "ep_ids8.json")); pick = set()
    for tag in ids:
        for eid in ids[tag]:
            p = S / f"live_replays3/episode-{eid}-replay.json"
            if not p.exists(): continue
            rep = json.load(open(p)); nm = rep["info"]["TeamNames"]
            if nm.count("datatuu") != 1: continue
            o = 1 - nm.index("datatuu"); m1 = [x for x in (rep["steps"][1][o].get("action") or {}).get("market") or [] if x]
            if (tuple(int(x[2]) for x in m1 if x[0] == "BUY_PRODUCT" and len(x) > 2), tuple(int(x[2]) for x in m1 if x[0] == "SELL" and len(x) > 2)) == ((13, 30), (30,)):
                pick.add(eid)
    jobs = [(e, v) for e in sorted(pick) for v in ("y68v", "op_b30")]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=2))
    tab = {}
    for eid, opp, ver, mis, h30, m, live in res:
        d = tab.setdefault(eid, {"opp": opp, "live": live}); d[ver] = (m, h30, mis)
    print(f"{'对手':16s} {'线上':>7s} {'y68v':>8s} {'d1帮工':>7s} {'op_b30':>8s} {'d1帮工':>7s} 开局期对手与V38不一致步")
    for eid, d in sorted(tab.items(), key=lambda kv: kv[1]["y68v"][0]):
        print(f"{d['opp'][:16]:16s} {d['live']:+7.0f} {d['y68v'][0]:+8.0f} {str(d['y68v'][1]):>7s} {d['op_b30'][0]:+8.0f} {str(d['op_b30'][1]):>7s} {d['y68v'][2]}")
    for v in ("y68v", "op_b30"):
        ms = [d[v][0] for d in tab.values()]
        print(f"汇总 {v}: {sum(x>0 for x in ms)}/{len(ms)} 总 {sum(ms):+.0f}")
    print(f"线上实际: {sum(d['live']>0 for d in tab.values())}/{len(tab)} 总 {sum(d['live'] for d in tab.values()):+.0f}")
