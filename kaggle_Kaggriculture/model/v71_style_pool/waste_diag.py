"""方向0 诊断:我方 vs 代表 同局对比 —— 终局未卖出货值、最后 3 天投入/产出、各产品卖出量与均价、雇工。双席位大种子。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
PR=("WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER")
def one(job):
    agent,opp,seed,seat=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[opp]).parent))
    import fidelity, engine
    try:
        A={seat:fidelity.make_agent(f"sub:{HERE}/agents/{agent}_main.py"),1-seat:fidelity.make_agent(f"sub:{OPP[opp]}")}
        k=engine.load_kagsim(); g=k.Game(seed=seed); t=0
        F=[collections.Counter(),collections.Counter()]
        last=None
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[A[0](obs[0]),A[1](obs[1])]
            pr=obs[0]["market"]["prices"]
            for p in (0,1):
                i=0 if p==seat else 1
                for x in ((a[p] or {}).get("market") or []):
                    if not x: continue
                    try: n=int(x[2]) if len(x)>2 else 1
                    except Exception: n=1
                    late = t>=648
                    if x[0]=="SELL" and x[1] in pr:
                        F[i]["sq_"+x[1]]+=n; F[i]["s$_"+x[1]]+=n*pr[x[1]]
                    elif x[0]=="BUY_ANIMAL": F[i]["late_animal" if late else "animal"]+=n
                    elif x[0]=="BUY_SEED": F[i]["late_seed" if late else "seed"]+=n
                    elif x[0]=="HIRE": F[i]["late_hire" if late else "hire"]+=1
                    elif x[0]=="BUY_LAND": F[i]["land"]+=1
            last=obs
            g.step(a[0],a[1]); t+=1
        out={}
        for p in (0,1):
            i=0 if p==seat else 1
            ob=g.observe(p); pr=ob["market"]["prices"]; inv=collections.Counter(ob["private"]["shed"])
            for u in ob["private"].get("inventories") or []:
                for kk,v in (u or {}).items(): inv[kk]+=v
            F[i]["leftover$"]=sum(inv[x]*pr.get(x,0) for x in PR)
            F[i]["leftover_items"]=sum(inv[x] for x in PR)
            F[i]["reward"]=float(g.reward(p))
        return job,dict(me=dict(F[0]),op=dict(F[1]),d=F[0]["reward"]-F[1]["reward"])
    except Exception as ex: return job,None
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    agent=sys.argv[1]; opps=sys.argv[2].split(",")
    jobs=[(agent,o,IDX[c][2],st) for o in opps for c in cells for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(one,jobs,chunksize=2))
    json.dump({f"{j[1]}|{j[2]}|{j[3]}":v for j,v in R.items() if v},open(f"waste_{agent}.json","w"))
    for o in opps+["合计"]:
        V=[v for j,v in R.items() if v and (o=="合计" or j[1]==o)]
        for nm,S in (("惜败(<2k)",[v for v in V if -2000<v["d"]<0]),("大败",[v for v in V if v["d"]<=-2000]),("胜",[v for v in V if v["d"]>0])):
            if not S: continue
            av=lambda side,k: sum(x[side].get(k,0) for x in S)/len(S)
            items=[("终局剩货$","leftover$"),("剩货件","leftover_items"),("末3天买畜","late_animal"),("末3天买种","late_seed"),("末3天雇工","late_hire"),("买地","land"),("雇工","hire")]
            print(f"[{o}] {nm} n={len(S)} 均差 {sum(x['d'] for x in S)/len(S):.0f} | "+" ".join(f"{a}:{av('me',k):.1f}/{av('op',k):.1f}" for a,k in items))
            prod=[]
            for x in PR:
                qm,qo=av('me','sq_'+x),av('op','sq_'+x)
                if qm+qo<1: continue
                pm=av('me','s$_'+x)/max(1e-9,qm); po=av('op','s$_'+x)/max(1e-9,qo)
                prod.append(f"{x[:4]} 量{qm:.0f}/{qo:.0f} 价{pm:.0f}/{po:.0f} 额差{av('me','s$_'+x)-av('op','s$_'+x):+.0f}")
            print("      "+" | ".join(prod))
