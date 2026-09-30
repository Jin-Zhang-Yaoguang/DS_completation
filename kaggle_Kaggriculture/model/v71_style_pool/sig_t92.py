"""二次指纹:我方 r22 视角下对手在 t48..t143 的现金序列,找能在 t144 前区分谱系的时点。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
AG=["rescue7","v54","v56","harvestledger","hybrid2965","hai2965","guru_v4","idleseller","pipe18","v40chal","v57fo","herdsafe","engineV3","shepledger","cha22","demandpres","evgen0924"]
def one(job):
    opp,seed=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[opp]).parent))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:{HERE}/agents/v54r22_main.py"); op=fidelity.make_agent(f"sub:{OPP[opp]}")
    k=engine.load_kagsim(); g=k.Game(seed=seed); tr=[]
    for t in range(144):
        obs=[g.observe(0),g.observe(1)]; tr.append(float(obs[0]["farms"][1]["money"]))
        g.step(me(obs[0]),op(obs[1]))
    return opp,seed,tr
if __name__=="__main__":
    jobs=[(o,s) for o in AG for s in (18001,18077,18333)]
    with ProcessPoolExecutor(3) as ex: res=list(ex.map(one,jobs))
    R={}
    for o,s,tr in res: R.setdefault(o,{})[s]=tr
    json.dump(R,open(HERE/"sig_t92.json","w"))
    base=R["rescue7"][18001]
    for o in AG:
        same=all(R[o][s]==R[o][18001] for s in R[o])
        d=next((t for t in range(144) if R[o][18001][t]!=base[t]),None)
        print(f"{o:14} 跨seed一致:{same}  与rescue7首差步:{d}  t{d}现金:{R[o][18001][d] if d is not None else '-'}  t92:{R[o][18001][92]} t120:{R[o][18001][120]} t143:{R[o][18001][143]}")
