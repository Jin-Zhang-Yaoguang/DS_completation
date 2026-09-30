"""w48 对 v54live 中 metav4 键(1052,9989)的 25 局 tape 重放。"""
import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
rows=json.load(open(HERE/"rival_freq.json"))
eps=[x["ep"] for x in rows if tuple(x["rkey"])==(1052.0,9989) and x["dir"]=="v54live"]
def one(fn):
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    r=json.load(open(fn)); nm=r["info"]["TeamNames"]; s=r["steps"]
    seat=nm.index("datatuu"); o=1-seat
    op=fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
    me=fidelity.make_agent(f"sub:{HERE}/agents/v54r3w48_main.py")
    k=engine.load_kagsim(); g=k.Game(seed=r["info"]["seed"])
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
    return Path(fn).name, float(g.reward(seat)-g.reward(o)), float(r["rewards"][seat]-r["rewards"][o])
if __name__=="__main__":
    fns=[str(HERE/"v54live"/f"episode-{e}-replay.json") for e in eps]
    print("局数",len(fns),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,fns))
    w=sum(1 for _,m,_ in res if m>0); lw=sum(1 for _,_,l in res if l>0)
    print(f"w48 重放 {w}/{len(res)} 胜 | 线上 V54 实际 {lw}/{len(res)} 胜")
    for n,m,l in sorted(res,key=lambda x:x[1])[:6]: print(f"  {n} 重放{m:+.0f} 线上{l:+.0f}")
