"""r5 唯一败局:对手 tape 重放 + 全候选带扫描。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
FN=str(HERE/"rlive"/"episode-111981662-replay.json")
CAND=[-1,0,1,3,4,5,6,7,8,9,10,11,12,100,101,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128]
def one(rid):
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(FN)); s=r["steps"]; nm=r["info"]["TeamNames"]
        seat=nm.index("datatuu"); o=1-seat
        op=fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=r["info"]["seed"])
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return rid, float(g.reward(seat)-g.reward(o))
    except Exception as e: return rid, f"ERR{type(e).__name__}"
if __name__=="__main__":
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,CAND))
    for rid,m in sorted(res,key=lambda x: -(x[1] if isinstance(x[1],float) else -9e9)):
        print(f"  带{rid:4d}  {m if isinstance(m,str) else format(m,'+.0f')}")
