"""我方开局改动后,观测到的各对手族 rkey 是否漂移(r17 vs r18)。"""
import sys, os, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
DB=M/"v58_mosaic"/"dist_backup"
OPPS={"v52":f"{HERE}/agents/v52_main.py","v53":f"{HERE}/agents/v53_main.py","v54":f"{HERE}/agents/v54_main.py",
      "v56":f"{HERE}/agents/v56_main.py","rescue7":f"{HERE}/agents/rescue7_main.py","busya":f"{HERE}/agents/busya_race_main.py",
      "herdsafe":f"{HERE}/agents/herdsafe_main.py","metav4":f"{HERE}/agents/metav4_main.py",
      "y68i":f"{DB}/y68i_main.py","y68s2":f"{DB}/y68s2_main.py"}
def one(job):
    ver,o,seed=job
    os.environ.pop("KAG_FORCE_ROUTE",None); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py"); op=fidelity.make_agent(f"sub:{OPPS[o]}")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        for t in range(3):
            obs=[g.observe(0),g.observe(1)]
            if t==2: return ver,o,(round(float(obs[0]["farms"][1]["money"]),3), int(obs[0]["market"]["inventory"]["WHEAT"]))
            g.step(me(obs[0]),op(obs[1]))
    except Exception as e: return ver,o,f"ERR {e}"
if __name__=="__main__":
    jobs=[(v,o,s) for v in ("v54r17","v54r18") for o in OPPS for s in (17000,17001)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs))
    d=collections.defaultdict(set)
    for v,o,rk in res: d[(o,v)].add(str(rk))
    print(f"{'对手':10s} {'r17 观测':28s} {'r18 观测':28s} 漂移?")
    for o in OPPS:
        a=sorted(d[(o,'v54r17')]); b=sorted(d[(o,'v54r18')])
        print(f"{o:10s} {str(a):28s} {str(b):28s} {'★漂移' if a!=b else ''}")
