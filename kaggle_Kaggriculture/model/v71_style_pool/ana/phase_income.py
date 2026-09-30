"""精确重放:按阶段统计双方每种产品卖出收入(卖出前后价格×量近似用当步报价)与支出。"""
import json,sys,os,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent; os.chdir(HERE); sys.path.insert(0,str(HERE))
from pub_splice import M
sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
import engine
k=engine.load_kagsim()
PH=[(0,216),(216,360),(360,504),(504,576),(576,720)]
def run(eid):
    r=json.load(open(f"rlive3/{eid}.json")); A=r["acts"]; s=r["seat"]; o=1-s
    g=k.Game(seed=r["seed"]); t=1
    inc={q:collections.defaultdict(collections.Counter) for q in (s,o)}; cost={q:collections.Counter() for q in (s,o)}
    while not engine._val(g.done) and t<len(A):
        ob=g.observe(0); pr=ob["market"]["prices"]; m0=[ob["farms"][0]["money"],ob["farms"][1]["money"]]
        g.step(A[t][0] or {},A[t][1] or {}); ob2=g.observe(0); m1=[ob2["farms"][0]["money"],ob2["farms"][1]["money"]]
        ph=next(i for i,(a,b) in enumerate(PH) if a<=t<b)
        for q in (s,o):
            sold=collections.Counter()
            for m in (A[t][q] or {}).get("market") or []:
                if m and m[0]=="SELL": sold[m[1]]+=m[2] if len(m)>2 else 1
            est={it:n*pr.get(it,0) for it,n in sold.items()}
            for it,v in est.items(): inc[q][ph][it]+=v
            other=(m1[q]-m0[q])-sum(est.values())
            cost[q][ph]+=other
        t+=1
    print("="*80,"\n",eid,r["names"][o],"d",r["rewards"][s]-r["rewards"][o])
    for i,(a,b) in enumerate(PH):
        for nm,q in (("我",s),("敌",o)):
            tot=sum(inc[q][i].values())
            print(f" [{a:3d}-{b:3d}) {nm} 市场卖出≈{tot:7.0f} 其他净(商店/买入/雇佣)={cost[q][i]:8.0f}  主要:{dict((x,round(y)) for x,y in inc[q][i].most_common(5))}")
for e in sys.argv[1].split(","): run(e)
