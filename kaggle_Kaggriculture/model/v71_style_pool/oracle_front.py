"""定向抢价上限(神谕):直接读取对手底盘当前路线,若对手未来 W 步计划卖 X,我方把未来 K 步计划卖的 X 立刻卖出(记预卖债务)。对照 r38g。"""
import sys, os, json, collections
from concurrent.futures import ProcessPoolExecutor
M="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model"
V71=M+"/v71_style_pool"
ITEMS=("CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER")
def load(path,entry):
    ns={"__name__":"m"}; exec(compile(open(path).read(),path,"exec"),ns); return ns,ns[entry]
def one(job):
    mode,opp,seed,seat,W,K=job
    sys.path.insert(0,M+"/v4_demand_race/harness"); import engine
    try:
        nsA,A=load(V71+"/agents/v54r38g_main.py","_lead_final")
        nsB,B=load(V71+f"/agents/{opp}_main.py","agent")
        chA=nsA["_IMPL"].chassis; chB=nsB["_IMPL"].chassis; o=1-seat
        k=engine.load_kagsim(); g=k.Game(seed=seed); t=0
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]
            a=[None,None]; a[o]=B(obs[o]); act=A(obs[seat])
            if mode=="oracle" and 144<=t<700 and isinstance(act,dict):
                try:
                    pB=chB.players.get(o) or {}; rB=(pB.get("router_state") or {}).get("route",pB.get("route"))
                    pA=chA.players.get(seat) or {}; rA=(pA.get("router_state") or {}).get("route",pA.get("route"))
                    st=nsA["_LEAD_STATE"].get(seat); debt=st["debt"] if st else {}
                    market=act.setdefault("market",[]); shed=obs[seat]["private"]["shed"]
                    for it in ITEMS:
                        opp_soon=chB.future_sells(rB,it,t+1)-chB.future_sells(rB,it,t+1+W) if rB in chB.routes else 0
                        if opp_soon<=0: continue
                        queued=sum(int(x[2]) for x in market if x and x[0]=="SELL" and x[1]==it and len(x)>2)
                        avail=int(shed.get(it,0))-queued
                        ours=chA.future_sells(rA,it,t+1)-chA.future_sells(rA,it,t+1+K)-debt.get(it,0) if rA in chA.routes else 0
                        q=min(avail,ours)
                        if q<=0: continue
                        for x in market:
                            if x and x[0]=="SELL" and x[1]==it and len(x)>2: x[2]=int(x[2])+q; break
                        else:
                            if len(market)>=10: continue
                            market.append(["SELL",it,q])
                        debt[it]=debt.get(it,0)+q
                except Exception: pass
            a[seat]=act; g.step(a[0],a[1]); t+=1
        return job,float(g.reward(seat)-g.reward(o))
    except Exception as ex: return job,None
if __name__=="__main__":
    IDX=json.load(open(V71+"/combo_big.json"))["v54"]; cells=sorted(IDX)
    CFG=[(1,4),(2,8)]
    jobs=[]
    for opp in ("me2965_28","engineV3"):
        for c in cells:
            for i in (20,21):
                for st in (0,1):
                    jobs.append(("base",opp,IDX[c][i],st,0,0))
                    for W,K in CFG: jobs.append(("oracle",opp,IDX[c][i],st,W,K))
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(one,jobs,chunksize=2))
    for opp in ("me2965_28","engineV3"):
        base={(j[2],j[3]):v for j,v in R.items() if j[0]=="base" and j[1]==opp and v is not None}
        print(f"vs {opp}: r38g 胜 {sum(v>0 for v in base.values())}/{len(base)} 均差 {sum(base.values())/len(base):.0f}")
        for W,K in CFG:
            ora={(j[2],j[3]):v for j,v in R.items() if j[0]=="oracle" and j[1]==opp and j[4]==W and j[5]==K and v is not None}
            P=[(ora[k],base[k]) for k in ora if k in base]
            print(f"   神谕 W={W} K={K}: 胜 {sum(p>0 for p,_ in P)}/{len(P)} 均差 {sum(p for p,_ in P)/len(P):.0f}  翻盘 +{sum(1 for p,q in P if p>0>=q)} −{sum(1 for p,q in P if q>0>=p)}",flush=True)
