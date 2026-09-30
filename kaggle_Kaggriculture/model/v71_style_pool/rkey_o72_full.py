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
      "y68i":f"{DB}/y68i_main.py","y68s2":f"{DB}/y68s2_main.py","v55":f"{HERE}/agents/v55_main.py","shepherd":f"{HERE}/agents/shepherd_main.py","V41":f"{HERE}/agents/kernels_0914/v41_agent.py","V43":f"{HERE}/agents/kernels_0915/v43_agent.py","V38":f"{HERE}/agents/kernels_0913/v38_main.py","qq":f"{HERE}/agents/opp_qq_main.py","guru_v4":f"{HERE}/agents/guru_v4_main.py","multiroute":f"{HERE}/agents/multiroute_main.py","y68a":f"{DB}/y68a_main.py","y68j":f"{DB}/y68j_main.py","y68r2":f"{DB}/y68r2_main.py"}
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
    jobs=[(v,o,s) for v in ("op_o7_2",) for o in OPPS for s in (17000,)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs))
    d=collections.defaultdict(set)
    for v,o,rk in res: d[(o,v)].add(str(rk))
    vs=("op_o7_2",)
    print(f"{'对手':10s} " + " ".join(f"{v:22s}" for v in vs))
    for o in OPPS:
        print(f"{o:10s} " + " ".join(f"{str(sorted(d[(o,v)])):22s}" for v in vs))
    for v in vs:
        inv={}
        for o in OPPS:
            for k in d[(o,v)]: inv.setdefault(k,[]).append(o)
        clash={k:os_ for k,os_ in inv.items() if len(set(os_))>1 and not set(os_)<= {"v54","v56","rescue7","busya"} and not set(os_)<={"v52","v53"}}
        print(f"  {v} 撞键: {clash if clash else '无'}")
