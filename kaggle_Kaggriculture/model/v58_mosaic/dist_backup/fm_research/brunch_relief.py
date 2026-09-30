"""BRUNCH|FM 定向:y68x3 vs y68x4r(泄压提前到 t400),对 V43/V41/V43+B10,各用自己扫描的 BRUNCH|FM seed(≤10,双座位)。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
OPPS = {"V43": "kernels_0915/v43_agent.py", "V41": "kernels_0914/v41_agent.py", "V43+B10": "kernels_0915/v43b10_agent.py"}
def one(job):
    sd, seat, ver, opp = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py"); op = fidelity.make_agent(f"sub:{S}/{OPPS[opp]}")
    k = engine.load_kagsim(); g = k.Game(seed=sd); t = 0; combo = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1]); t += 1
        if t == 146: combo = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
    return sd, seat, ver, opp, combo, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    by_opp = json.load(open(S / "combo_seeds_by_opp.json"))
    v43scan = {}
    for f in ("combo_seeds_y68v.json", "combo_seeds_y68v_b.json"):
        for c, v in json.load(open(S / f)).items(): v43scan.setdefault(c, []).extend(v)
    seeds_for = {"V43": v43scan, "V41": v43scan, "V43+B10": by_opp["V43+B10"]}
    c = "BRUNCH_SPOT|FARMERS_MARKET"
    jobs = [(sd, seat, v, o) for o in OPPS for sd in seeds_for[o][c][:10] for seat in (0, 1) for v in ("y68x3", "y68x4r")]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=2))
    for o in OPPS:
        for v in ("y68x3", "y68x4r"):
            vals = [m for sd, st, vv, oo, cc, m in res if oo == o and vv == v and cc == c]
            print(f"{o:8s} {v:7s}: BRUNCH|FM {sum(x>0 for x in vals)}/{len(vals)} 最差{min(vals):+6.0f} 均{statistics.mean(vals):+6.0f}")
