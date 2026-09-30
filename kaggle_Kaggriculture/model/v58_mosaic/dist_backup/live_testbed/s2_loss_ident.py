"""y68s2 输局对手身份:我方固定线上动作,对手动作 vs 原版 V38/V41/V42/V43 反应式,统计不一致步。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
AG = {"v38": "kernels_0913/v38_main.py", "v41": "kernels_0914/v41_agent.py", "v42": "kernels_0914/v42_agent.py", "v43": "kernels_0915/v43_agent.py"}
def norm(a):
    a = a or {}
    return json.dumps({"f": a.get("farmer") or ["PASS"], "h": a.get("hands") or [], "m": a.get("market") or []}, sort_keys=True)
def one(job):
    eid, ver = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    rep = json.load(open(S / f"live_replays3/episode-{eid}-replay.json"))
    nm = rep["info"]["TeamNames"]; seat = nm.index("datatuu"); o = 1 - seat; st = rep["steps"]
    live_me = [st[t + 1][seat].get("action") or {} for t in range(len(st) - 1)]
    live_op = [st[t + 1][o].get("action") or {} for t in range(len(st) - 1)]
    me = fidelity.tape_agent(live_me); optape = fidelity.tape_agent(live_op)
    ag = fidelity.make_agent(f"sub:{S}/{AG[ver]}")
    k = engine.load_kagsim(); g = k.Game(seed=rep["info"]["seed"]); t = 0; mis = []
    while not engine._val(g.done) and t < len(live_op):
        obs = [g.observe(0), g.observe(1)]
        try: a = ag(obs[o])
        except Exception: a = {}
        if norm(a) != norm(live_op[t]): mis.append(t)
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[o] = optape(obs[o])
        g.step(acts[0], acts[1]); t += 1
    return eid, str(nm[o]), ver, len(mis), mis[:6]
if __name__ == "__main__":
    rows = json.load(open(S / "y68s2_check.json"))["y68s2"]
    losses = [r["ep"] for r in rows if r["m"] <= 0]
    jobs = [(e, v) for e in losses for v in AG]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs))
    for e in losses:
        rs = [r for r in res if r[0] == e]
        best = min(rs, key=lambda r: r[3])
        print(f"ep{e} vs {rs[0][1]}: " + " | ".join(f"{r[2]} 不一致{r[3]}" for r in rs) + f"  → 最接近 {best[2]},首批不一致步 {best[4]}")
