"""新版人群诊断:r38 vs 代表 在近期真实棋盘上复现,按品类分解双方收入/支出与关键时点现金。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
CK=(144,288,432,504,576,648,700)
def one(job):
    agent,opp,seed,seat,eid=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[opp]).parent))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{agent}_main.py"); op=fidelity.make_agent(f"sub:{OPP[opp]}")
        k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat; P=(seat,o)
        F=[collections.Counter(),collections.Counter()]; cash={}; t=0
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o])
            pr=obs[0]["market"]["prices"]
            for i,p in enumerate(P):
                for x in ((a[p] or {}).get("market") or []):
                    try:
                        if x[0]=="SELL": F[i]["卖_"+x[1]]+=x[2]*pr.get(x[1],0)
                        elif x[0]=="BUY_PRODUCT": F[i]["买货_"+x[1]]-=x[2]*pr.get(x[1],0)
                        elif x[0]=="BUY_ANIMAL": F[i]["买畜_"+x[1]]+=x[2]
                        elif x[0]=="BUY_SEED": F[i]["种子_"+x[1]]+=x[2]
                        elif x[0]=="HIRE": F[i]["雇工"]+=1
                        else: F[i]["其他_"+x[0]]+=1
                    except Exception: pass
            m0,m1=obs[0]["farms"][seat]["money"],obs[0]["farms"][o]["money"]
            if t in CK: cash[t]=(m0,m1)
            g.step(a[0],a[1]); t+=1
        return eid,dict(d=float(g.reward(seat)-g.reward(o)),F=[dict(F[0]),dict(F[1])],cash=cash)
    except Exception as ex: return eid,None
if __name__=="__main__":
    agent=sys.argv[1]; opp=sys.argv[2]; cls=sys.argv[3] if len(sys.argv)>3 else "新版人群"
    B=[x for x in json.load(open("axis_rows.json")) if x["cls"]==cls]
    jobs=[(agent,opp,x["seed"],x["seat"],x["eid"]) for x in B]
    with ProcessPoolExecutor(int(os.environ.get("KAG_WORKERS","8"))) as ex: R=dict(ex.map(one,jobs,chunksize=1))
    json.dump({"rows":B,"res":R},open(f"ngdiag_{agent}_{opp}_{cls}.json","w"),ensure_ascii=False)
    L=[e for e,v in R.items() if v and v["d"]<0]; W=[e for e,v in R.items() if v and v["d"]>0]
    print(f"{agent} vs {opp} [{cls}] {len(B)} 盘:模拟胜 {len(W)} 负 {len(L)}  近失(<2k) {sum(1 for e in L if R[e]['d']>-2000)}")
    for nm,S in (("负局",L),("胜局",W)):
        if not S: continue
        keys=collections.Counter()
        for e in S:
            for kk,v in R[e]["F"][0].items(): keys[kk]+=v
            for kk,v in R[e]["F"][1].items(): keys[kk]-=v
        print(f" {nm} n={len(S)} 我方-对手 平均差(按品类,卖/买货为金额,畜/种子/雇工为数量):")
        print("   ",{k:round(v/len(S)) for k,v in sorted(keys.items(),key=lambda kv:-abs(kv[1]))[:16]})
        print("    现金差中位:",{t:sorted(R[e]["cash"][t][0]-R[e]["cash"][t][1] for e in S if t in R[e]["cash"])[len(S)//2] for t in CK})
