"""反事实:精确重放线上对局,对手开环,我方去掉 t>=T 的 BUY_PRODUCT WHEAT(卖出按可得量截断),看终局分差变化。"""
import json,sys,os,copy
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent.parent; os.chdir(HERE); sys.path.insert(0,str(HERE))
from pub_splice import M
def sim(job):
    eid,T,mode=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import engine; k=engine.load_kagsim()
    r=json.load(open(f"rlive3/{eid}.json")); A=r["acts"]; s=r["seat"]; o=1-s
    g=k.Game(seed=r["seed"]); t=1
    while not engine._val(g.done) and t<len(A):
        a=[copy.deepcopy(A[t][0] or {}),copy.deepcopy(A[t][1] or {})]
        if t>=T:
            mk=a[s].get("market") or []
            if mode=="nobuy": mk=[m for m in mk if not (m and m[0]=="BUY_PRODUCT" and m[1]=="WHEAT")]
            if mode=="clampsell":
                sh=g.observe(s)["private"]["shed"]; 
                mk=[m for m in mk if not (m and m[0]=="BUY_PRODUCT" and m[1]=="WHEAT")]
            a[s]["market"]=mk
        g.step(a[0],a[1]); t+=1
    return eid,T,mode,float(g.reward(s)-g.reward(o))
if __name__=="__main__":
    IDX=json.load(open("online_games.json"))
    E=[e for e,v in IDX.items() if v["ver"]=="v55b"]
    jobs=[(e,T,"nobuy") for e in E for T in (216,360,504,576)]+[(e,9999,"base") for e in E]
    with ProcessPoolExecutor(8) as ex: R=list(ex.map(sim,jobs))
    D={}
    for e,T,m,d in R: D.setdefault(e,{})[T]=d
    tot={T:0 for T in (216,360,504,576)}; flips={T:[0,0] for T in tot}
    for e in E:
        b=D[e][9999]; line=f"{e} {IDX[e]['opp_team'][:14]:14s} 基线{b:+8.0f} "
        for T in tot:
            x=D[e][T]; tot[T]+=x-b; flips[T][0]+= (b<0<x); flips[T][1]+=(b>0>x); line+=f" 去t{T}后买麦:{x-b:+7.0f}"
        print(line)
    print("合计变化",{T:round(v/len(E)) for T,v in tot.items()},"翻盘(负→胜,胜→负)",flips)
