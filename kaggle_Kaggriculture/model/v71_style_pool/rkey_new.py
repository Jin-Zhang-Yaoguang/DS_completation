# 新代理 rkey 指纹(同 rkey_lib 口径)
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
K = HERE/"kernels_0922"
AGENTS = {"V55": K/"kaggriculture-v55-one-turn-market-race-edge_main.py",
          "V56": K/"kaggriculture-v56-smarter-seeds-and-fertilizer_main.py",
          "busya_race": K/"busya_race_main.py",
          "busya_seedfloat": K/"busya_seedfloat_main.py",
          "guru_v4": K/"kaggriculture-top-2-master-engine-v4_main.py",
          "multiroute": K/"kaggriculture-multi-route-farming-agent_main.py",
          "metav4_v13": K/"the-metav4-farm-submission-v13_main.py",
          "hai2965": K/"the-2965-master-hybrid-engine_main.py",
          "evgen": K/"kaggriculture_main.py"}
def one(job):
    name, path, seed = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me = fidelity.make_agent(f"sub:{HERE}/agents/v54_main.py"); op = fidelity.make_agent(f"sub:{path}")
        k = engine.load_kagsim(); g = k.Game(seed=seed)
        for t in range(3):
            obs = [g.observe(0), g.observe(1)]
            if t == 2:
                rv = obs[0]["farms"][1]
                return name, seed, (round(float(rv["money"]),3), int(obs[0]["market"]["inventory"]["WHEAT"]))
            g.step(me(obs[0]), op(obs[1]))
    except Exception as e:
        return name, seed, f"ERR {type(e).__name__}: {e}"
if __name__ == "__main__":
    jobs = [(n, str(p), s) for n,p in AGENTS.items() for s in (9100,9101,9102)]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    import collections
    lib = collections.defaultdict(set)
    for n,s,rk in res: lib[n].add(rk if isinstance(rk,str) else str(rk))
    for n,v in lib.items(): print(f"{n:16s} {sorted(v)}")
