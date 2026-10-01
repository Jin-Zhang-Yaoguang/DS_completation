"""精确重放线上对局(双方记录动作),打印检查点双方资金/库存/地块内容。"""
import json,sys,os,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent; os.chdir(HERE); sys.path.insert(0,str(HERE))
from pub_splice import M
sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
import engine
k=engine.load_kagsim()
def tiles(f):
    c=collections.Counter()
    for row in f["tiles"]:
        for x in row:
            if x is None or x=="LOCKED": continue
            if isinstance(x,dict): c[x.get("type","?")+":"+str(x.get("crop") or x.get("animal") or x.get("kind") or "")]+=1
            else: c[str(x)]+=1
    return dict(c)
for eid in sys.argv[1].split(","):
    r=json.load(open(f"rlive3/{eid}.json")); A=r["acts"]; s=r["seat"]; o=1-s
    g=k.Game(seed=r["seed"]); t=1; CP=set(int(x) for x in (sys.argv[2] if len(sys.argv)>2 else "504,576,648,700,718").split(","))
    print("="*90,"\n",eid,r["names"][o],"我方seat",s)
    while not engine._val(g.done) and t<len(A):
        g.step(A[t][0] or {},A[t][1] or {}); 
        if t in CP:
            for nm,q in (("我",s),("敌",o)):
                ob=g.observe(q); f=ob["farms"][q]
                sh={a:b for a,b in ob["private"]["shed"].items() if b}; sd={a:b for a,b in ob["private"]["seeds"].items() if b}
                print(f" t{t} {nm} 钱{f['money']:.0f} 库存{sh} 种子{sd}\n        地块{tiles(f)}")
        t+=1
    print(" 终局奖励",[float(g.reward(0)),float(g.reward(1))],"线上",r["rewards"])
