"""FM 全面验证:指定版本 × 15 个 FM 组合全部 seed(≤10,座位交替)× 6 类对手。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
VERS = sys.argv[1].split(",")
OPPS = {"V38原版": "kernels_0913/v38_main.py", "V41": "kernels_0914/v41_agent.py", "V43": "kernels_0915/v43_agent.py",
        "V43+B10": "kernels_0915/v43b10_agent.py", "V43+13/13": "opp_v43_1313_main.py", "qq型": "opp_qq_main.py"}
def one(job):
    combo, sd, seat, ver, opp = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py"); op = fidelity.make_agent(f"sub:{S}/{OPPS[opp]}")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1])
    return combo, sd, seat, ver, opp, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    by = json.load(open(S / "combo_seeds_y68v.json"))
    fm = sorted(c for c in by if "FARMERS_MARKET" in c.split("|"))
    jobs = [(c, sd, i % 2, v, o) for c in fm for i, sd in enumerate(by[c][:10]) for v in VERS for o in OPPS]
    print(f"任务 {len(jobs)} 局", flush=True)
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=4))
    tag = "_".join(VERS)
    json.dump(res, open(S / f"fm_full_{tag}.json", "w"), ensure_ascii=False)
    for v in VERS:
        print(f"\n===== {v} =====")
        print(f"{'组合':32s} " + " ".join(f"{o:>14s}" for o in OPPS))
        tot = {o: [0, 0] for o in OPPS}
        for c in fm:
            cells = []
            for o in OPPS:
                vals = [m for cc, sd, st, vv, oo, m in res if cc == c and vv == v and oo == o]
                w = sum(x > 0 for x in vals); tot[o][0] += w; tot[o][1] += len(vals)
                mark = "" if w == len(vals) else "✗"
                cells.append(f"{w}/{len(vals)}{mark} {min(vals):+6.0f}")
            print(f"{c:32s} " + " ".join(f"{x:>14s}" for x in cells))
        print(f"{'合计':32s} " + " ".join(f"{tot[o][0]:>6d}/{tot[o][1]:<7d}" for o in OPPS))
