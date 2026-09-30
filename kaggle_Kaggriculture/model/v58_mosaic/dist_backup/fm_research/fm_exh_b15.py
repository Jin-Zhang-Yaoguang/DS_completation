"""b15 类路线穷举:4 个仍有漏洞的 FM 组合 × 41 路线 × 新扫 seed(≤12,座位交替)× 对手 V43 与 V41。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
COMBOS = ["BRUNCH_SPOT|FARMERS_MARKET", "FARMERS_MARKET|BAKERY", "FARMERS_MARKET|BRUNCH_SPOT", "FARMERS_MARKET|ICE_CREAM_SHOP"]
OPPS = {"V43": "kernels_0915/v43_agent.py", "V41": "kernels_0914/v41_agent.py"}
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
    ns = {}; exec((S / "y68v_main.py").read_text(), ns)
    rids = sorted(ns["_IMPL"].chassis.routes)
    assert all((S / f"fr_{r}_main.py").exists() for r in rids)
    by = json.load(open(S / "combo_seeds_y68v_b.json"))
    jobs = [(c, sd, i % 2, v, o) for c in COMBOS for i, sd in enumerate(by[c][:12]) for v in ["y68x"] + [f"fr_{r}" for r in rids] for o in OPPS]
    print(f"任务 {len(jobs)} 局", flush=True)
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=8))
    json.dump(res, open(S / "fm_exh_b15.json", "w"), ensure_ascii=False)
    for c in COMBOS:
        def stat(v):
            out = {}
            for o in OPPS:
                vals = [m for cc, sd, st, vv, oo, m in res if cc == c and vv == v and oo == o]
                out[o] = (sum(x > 0 for x in vals), len(vals), min(vals), statistics.mean(vals))
            return out
        vers = ["y68x"] + [f"fr_{r}" for r in rids]
        ranked = sorted(vers, key=lambda v: (sum(stat(v)[o][0] for o in OPPS), min(stat(v)[o][2] for o in OPPS)), reverse=True)
        print(f"\n{c}")
        for v in (["y68x"] + [x for x in ranked if x != "y68x"][:6]):
            s = stat(v)
            print(f"   {v:8s} " + " | ".join(f"{o} {s[o][0]}/{s[o][1]} 最差{s[o][2]:+6.0f} 均{s[o][3]:+6.0f}" for o in OPPS))
