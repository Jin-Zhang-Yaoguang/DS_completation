"""换底盘评估:V54 vs V56 头对头;两底盘对同一对手集的配对分差。"""
import sys, json, statistics, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
DB = M/"v58_mosaic"/"dist_backup"
def one(job):
    me_p, op_p, seed, seat = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me = fidelity.make_agent(f"sub:{me_p}"); op = fidelity.make_agent(f"sub:{op_p}")
        k = engine.load_kagsim(); g = k.Game(seed=seed); o = 1-seat; a=[None,None]
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return job, float(g.reward(seat)-g.reward(o))
    except Exception as e:
        return job, None
if __name__=="__main__":
    A=str(HERE/"agents/v54_main.py"); B=str(HERE/"agents/v56_main.py")
    OPPS={"y68i":f"{DB}/y68i_main.py","y68s2":f"{DB}/y68s2_main.py",
          "v55":str(HERE/"agents/v55_main.py"),"busya_race":str(HERE/"agents/busya_race_main.py"),
          "guru_v4":str(HERE/"agents/guru_v4_main.py"),"metav4":str(HERE/"agents/metav4_main.py")}
    jobs=[(A,B,s,st) for s in range(9800,9816) for st in (0,1)]  # 头对头 32 局
    jobs+= [(me,op,s,0) for me in (A,B) for op in OPPS.values() for s in range(9800,9812)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one, jobs, chunksize=2))
    h2h=[m for (mp,op,s,st),m in res if op==B and m is not None]
    print(f"V54 vs V56 头对头 {len(h2h)} 局: V54 胜 {sum(1 for m in h2h if m>0)} | V56 胜 {sum(1 for m in h2h if m<0)} | 平 {sum(1 for m in h2h if m==0)}")
    per=collections.defaultdict(dict)
    for (mp,op,s,st),m in res:
        if mp in (A,B) and op!=B and m is not None:
            name=[k for k,v in OPPS.items() if v==op][0]
            per[(name,s)]["v54" if mp==A else "v56"]=m
    agg=collections.defaultdict(lambda:[0,0,0,[]])
    for (name,s),v in per.items():
        if "v54" in v and "v56" in v:
            a=agg[name]; a[0]+=v["v54"]>0; a[1]+=v["v56"]>0; a[2]+=1; a[3].append(v["v56"]-v["v54"])
    for name,a in sorted(agg.items()):
        print(f"{name:12s} 局{a[2]:2d}  V54胜{a[0]:2d} V56胜{a[1]:2d}  配对分差中位 {statistics.median(a[3]):+8.0f}")
