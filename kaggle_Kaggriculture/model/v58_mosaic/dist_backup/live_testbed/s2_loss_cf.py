"""y68s2 输局:分段钱差/工人 + 反事实(线上 seed,对手线上 tape)。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
VARS = ["y68s2", "y68r2", "s2_nobl", "s2_old"]
def one(job):
    eid, var = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    rep = json.load(open(S / f"live_replays3/episode-{eid}-replay.json"))
    nm = rep["info"]["TeamNames"]; seat = nm.index("datatuu"); o = 1 - seat; st = rep["steps"]
    me = fidelity.make_agent(f"sub:{S}/{var}_main.py")
    op = fidelity.tape_agent([st[t + 1][o].get("action") or {} for t in range(len(st) - 1)])
    k = engine.load_kagsim(); g = k.Game(seed=rep["info"]["seed"]); t = 0; seg = []
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[o] = op(obs[o])
        g.step(acts[0], acts[1]); t += 1
        if t % 72 == 0:
            f = g.observe(0)["farms"]
            seg.append((t, (f[seat].get("money") or 0) - (f[o].get("money") or 0), 1 + len(f[seat].get("hands") or []), 1 + len(f[o].get("hands") or [])))
    return eid, var, g.reward(seat) - g.reward(o), seg
if __name__ == "__main__":
    rows = json.load(open(S / "y68s2_check.json"))["y68s2"]
    losses = [r for r in sorted(rows, key=lambda r: r["m"]) if r["m"] <= 0]
    jobs = [(r["ep"], v) for r in losses for v in VARS]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs))
    for r in losses:
        print(f"\n== ep{r['ep']} vs {r['opp']} 线上 {r['m']:+.0f} | {r['shops']} 黑名单={r['bl']} 对手开局 {r['op_open']}")
        base = next(x for x in res if x[0] == r["ep"] and x[1] == "y68s2")
        prev = 0; line = []
        for t, d, mw, ow in base[3]:
            line.append(f"d{t//24}:{d-prev:+.0f}(工{mw}v{ow})"); prev = d
        print("   y68s2 分段钱差Δ:", " ".join(line))
        print("   反事实 margin:", " | ".join(f"{x[1]} {x[2]:+.0f}" for x in res if x[0] == r["ep"]))
