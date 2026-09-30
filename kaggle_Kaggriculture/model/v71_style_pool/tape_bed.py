import sys, json, glob
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
VERS = sys.argv[1].split(",")
N = int(sys.argv[2]) if len(sys.argv) > 2 else 60
def one(job):
    fn, ver = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    rep = json.load(open(fn)); st = rep["steps"]; nm = rep["info"]["TeamNames"]
    seat = nm.index("datatuu"); o = 1 - seat
    op = fidelity.tape_agent([st[t+1][o].get("action") or {} for t in range(len(st)-1)])
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=rep["info"]["seed"])
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
    return nm[o], ver, float(g.reward(seat)-g.reward(o)), float(rep["rewards"][seat]-rep["rewards"][o])
if __name__ == "__main__":
    fs=[f for f in sorted(glob.glob(str(S/"b13live"/"episode-*.json")))
        if json.load(open(f))["info"]["TeamNames"].count("datatuu")==1][:N]
    jobs=[(f,v) for f in fs for v in VERS]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs))
    tab={}
    for n,v,m,live in res: tab.setdefault((n,live),{})[v]=m
    import statistics as st
    for v in VERS:
        ms=[d[v] for d in tab.values()]
        print(f"{v:10s} {sum(m>0 for m in ms):3d}/{len(ms)} 总{sum(ms):+9.0f} 中位{st.median(ms):+8.0f}")
    print("线上原始    ", f"{sum(1 for (n,live) in tab if live>0)}/{len(tab)}")
    json.dump([list(r) for r in res], open(S/"tape_bed.json","w"), ensure_ascii=False)
