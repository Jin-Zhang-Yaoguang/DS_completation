"""公开新 agent 在我方 r22(7/2 开局)视角下的 rkey。"""
import sys, json, os, glob
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
def one(job):
    name,path,seed=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    sys.path.insert(0,str(Path(path).parent)); os.chdir(Path(path).parent)
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54r22_main.py"); op=fidelity.make_agent(f"sub:{path}")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        for t in range(3):
            obs=[g.observe(0),g.observe(1)]
            if t==2: return name,seed,(float(obs[0]["farms"][1]["money"]),int(obs[0]["market"]["inventory"]["WHEAT"]))
            g.step(me(obs[0]),op(obs[1]))
    except Exception as e: return name,seed,"ERR "+str(e)[:100]
if __name__=="__main__":
    paths={Path(p).relative_to(HERE/"agents/pub0925").parts[0].split("__")[-1][:40]:p for p in glob.glob(str(HERE/"agents/pub0925/*/main.py"))+glob.glob(str(HERE/"agents/pub0925/*/*/main.py"))}
    for extra in sys.argv[1:]: paths[Path(extra).stem]=str(HERE/extra)
    jobs=[(n,p,s) for n,p in paths.items() for s in (9100,9101)]
    with ProcessPoolExecutor(3) as ex: res=list(ex.map(one,jobs))
    import collections; d=collections.defaultdict(set)
    for n,s,rk in res: d[n].add(str(rk))
    for n,v in sorted(d.items()): print(f"{n:42} {sorted(v)}")
