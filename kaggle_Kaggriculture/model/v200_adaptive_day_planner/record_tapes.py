"""M1 数据:录制带子对局的逐步完整轨迹(单位位置、指令、背包、仓库、现金、地块),供日规划器离线建题与对比。"""
import sys, json, gzip
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = HERE.parent
HARNESS = [str(M / "v16_online_fidelity"), str(M / "v4_demand_race" / "harness")]

def record(job):
    seed, seat, me, opp = job
    for h in HARNESS: sys.path.insert(0, h)
    import fidelity, engine
    a_me = fidelity.make_agent(f"sub:{HERE}/agents/{me}_main.py"); a_op = fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat
    steps = []
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = a_me(obs[seat]); acts[o] = a_op(obs[o])
        ob = obs[seat]; f = ob["farms"][seat]; pr = ob.get("private") or {}
        steps.append(dict(
            units=[list(f["farmer"])] + [list(h) for h in f["hands"]],
            cmds=[acts[seat].get("farmer") or ["PASS"]] + [list(c) for c in (acts[seat].get("hands") or [])],
            market=[list(x) for x in (acts[seat].get("market") or [])],
            inv=pr.get("inventories") or [], shed=pr.get("shed") or {}, seeds=pr.get("seeds") or {},
            money=f["money"], tiles=f["tiles"]))
        g.step(acts[0], acts[1])
    out = HERE / "data" / f"tape_{me}_vs_{opp}_s{seed}_p{seat}.json.gz"
    with gzip.open(out, "wt") as w:
        json.dump(dict(seed=seed, seat=seat, me=me, opp=opp, bank=[float(g.reward(seat)), float(g.reward(o))], steps=steps), w)
    return str(out.name), g.reward(seat) - g.reward(o)

if __name__ == "__main__":
    jobs = [(s, s % 2, "y68x3b13", o) for s in range(1100, 1106) for o in ("y68s2", "y68r2")]
    with ProcessPoolExecutor(7) as ex:
        for name, m in ex.map(record, jobs): print(name, f"{m:+.0f}")
