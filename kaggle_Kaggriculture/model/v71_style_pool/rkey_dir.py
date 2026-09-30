"""线上口径:r38 为我方 seat0,候选为 seat1,第 2 步后我方观测到的对手现金与市场小麦库存;多种子。"""
import sys, glob, os
from pathlib import Path
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
import fidelity, engine
me=fidelity.make_agent(f"sub:{Path('agents/v54r38_main.py').resolve()}")
for p in sorted(glob.glob(sys.argv[1]+"/**/main.py",recursive=True)):
    try:
        sys.path.insert(0,str(Path(p).parent)); ks=[]
        for sd in (1500000017,1700000033):
            a=fidelity.make_agent(f"sub:{p}"); k=engine.load_kagsim(); g=k.Game(seed=sd)
            for t in range(2): o0=g.observe(0); o1=g.observe(1); g.step(me(o0),a(o1))
            ob=g.observe(0); ks.append((round(ob["farms"][1]["money"]),ob["market"]["inventory"]["WHEAT"]))
        print(ks, p.split(sys.argv[1])[-1][:90])
    except Exception as e: print("ERR",str(e)[:60],p.split(sys.argv[1])[-1][:80])
    finally: sys.path.pop(0)
