import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
K = HERE/"kernels_0922"
AGENTS = {"guru_v4":"guru_v4_main.py","fieldcraft":"kaggriculture-2887-score-fieldcraft-agent_main.py",
 "hai2950":"the-2950-peak-farm_main.py","lynn_wheat":"farmer-john-and-the-wheat-seller_main.py",
 "dmitrii":"kaggriculture-more-wheat-smarter-sales_main.py","xuan_top1":"kaggriculture-auto-top1_main.py",
 "guru_v3":"kaggriculture-master-engine-v3_main.py","pipe19":"kaggriculture-pipe19-sale-advance-overflow_main.py",
 "tetsu":"demand-preserving-turn-sale-timing_main.py","anhad":"kaggriculture-autonomous-ai-farming-agent_main.py"}
def one(job):
    name, path, seed = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me = fidelity.make_agent(f"sub:{HERE}/agents/v54_main.py"); op = fidelity.make_agent(f"sub:{K}/{path}")
        k = engine.load_kagsim(); g = k.Game(seed=seed)
        for t in range(3):
            obs = [g.observe(0), g.observe(1)]
            if t == 2:
                rv = obs[0]["farms"][1]
                return name, seed, str((round(float(rv["money"]),3), int(obs[0]["market"]["inventory"]["WHEAT"])))
            g.step(me(obs[0]), op(obs[1]))
    except Exception as e:
        return name, seed, f"ERR {type(e).__name__}"
if __name__ == "__main__":
    jobs = [(n,p,s) for n,p in AGENTS.items() for s in (9100,9101)]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    import collections
    lib = collections.defaultdict(set)
    for n,s,rk in res: lib[n].add(rk)
    for n,v in sorted(lib.items()): print(f"{n:12s} {sorted(v)}")
