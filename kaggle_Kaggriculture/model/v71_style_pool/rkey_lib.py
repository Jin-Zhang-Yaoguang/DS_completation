import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
DB = M / "v58_mosaic" / "dist_backup"
AGENTS = {"v52": f"{HERE}/agents/v52_main.py", "v53": f"{HERE}/agents/v53_main.py", "v54": f"{HERE}/agents/v54_main.py",
          "V43": f"{HERE}/agents/kernels_0915/v43_agent.py", "V41": f"{HERE}/agents/kernels_0914/v41_agent.py",
          "V38": f"{HERE}/agents/kernels_0913/v38_main.py", "V38_1313": f"{HERE}/agents/opp_v38_1313_main.py",
          "qq": f"{HERE}/agents/opp_qq_main.py", "y68s2": f"{DB}/y68s2_main.py", "y68r2": f"{DB}/y68r2_main.py",
          "y68wk5": f"{DB}/y68wk5_main.py", "y68x3b13": f"{DB}/y68x3b13_main.py"}
def one(job):
    name, path, seed = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{HERE}/agents/v54_main.py"); op = fidelity.make_agent(f"sub:{path}")
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    for t in range(3):
        obs = [g.observe(0), g.observe(1)]
        if t == 2:
            rv = obs[0]["farms"][1]
            return name, seed, (round(float(rv["money"]), 3), int(obs[0]["market"]["inventory"]["WHEAT"]))
        g.step(me(obs[0]), op(obs[1]))
    return name, seed, None
if __name__ == "__main__":
    jobs = [(n, p, s) for n, p in AGENTS.items() for s in (9100, 9101, 9102)]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    import collections
    lib = collections.defaultdict(set)
    for n, s, rk in res: lib[n].add(rk)
    out = {n: sorted(map(str, v)) for n, v in lib.items()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    json.dump(out, open(HERE/"rkey_lib.json", "w"), ensure_ascii=False)
