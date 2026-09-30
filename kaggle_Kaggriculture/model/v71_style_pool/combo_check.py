"""组合标签核对:combo_index6 标注的组合 vs 实际对局(我方 r34 vs me2965_28)t146 的真实组合。"""
import sys, json, random
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
def one(job):
    seed,label,me_ag,op_ag=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:agents/{me_ag}_main.py"); op=fidelity.make_agent(f"sub:agents/{op_ag}_main.py")
    k=engine.load_kagsim(); g=k.Game(seed=seed)
    for t in range(146):
        obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
    real="|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
    return seed,label,real
if __name__=="__main__":
    IDX=json.load(open("combo_index6.json"))["v54"]; pick=json.load(open("milk34_pick.json"))
    jobs=[(IDX[c][i],c,"v54r34","me2965_28") for c in pick for i in range(18,22) if i<len(IDX[c])]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs))
    same=sum(1 for s,l,r in res if l==r)
    print(f"r34 vs me2965_28:标签与实际组合一致 {same}/{len(res)}")
    for s,l,r in res[:8]: print("  ",s,"标签",l,"实际",r)
