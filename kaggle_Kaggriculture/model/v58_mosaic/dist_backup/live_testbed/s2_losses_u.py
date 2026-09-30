"""y68s2 线上 4 个输局重跑:y68s2 / y68u / y68u_fn。Yiwei Pu(原版 V41)用反应式对手,其余用对手线上 tape。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
def one(job):
    eid, ver, mode = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    rep = json.load(open(S / f"live_replays3/episode-{eid}-replay.json"))
    nm = rep["info"]["TeamNames"]; seat = nm.index("datatuu"); o = 1 - seat; st = rep["steps"]
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py")
    op = fidelity.make_agent(f"sub:{S}/kernels_0914/v41_agent.py") if mode == "v41" else fidelity.tape_agent([st[t + 1][o].get("action") or {} for t in range(len(st) - 1)])
    k = engine.load_kagsim(); g = k.Game(seed=rep["info"]["seed"])
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[o] = op(obs[o])
        g.step(acts[0], acts[1])
    return eid, str(nm[o]), ver, mode, g.reward(seat) - g.reward(o), rep["rewards"][seat] - rep["rewards"][o]
if __name__ == "__main__":
    rows = json.load(open(S / "y68s2_check.json"))["y68s2"]
    losses = [r for r in rows if r["m"] <= 0]
    jobs = []
    for r in losses:
        mode = "v41" if r["opp"].startswith("Yiwei") else "tape"
        for v in ("y68s2", "y68u", "y68u_fn"):
            jobs.append((r["ep"], v, mode))
    with ProcessPoolExecutor(6) as ex:
        res = list(ex.map(one, jobs))
    for r in losses:
        rs = [x for x in res if x[0] == r["ep"]]
        print(f"{rs[0][1][:16]:16s} 线上 {rs[0][5]:+6.0f} 对手={rs[0][3]:4s} | " + " | ".join(f"{x[2]} {x[4]:+.0f}" for x in rs))
