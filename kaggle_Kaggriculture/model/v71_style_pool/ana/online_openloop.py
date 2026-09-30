"""线上 v55b 对局反事实:同种子同席位,对手按线上记录动作开环回放,我方换成候选 agent。对固定带对手精确,对闭环对手近似。"""
import json,sys,os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent.parent; os.chdir(HERE); sys.path.insert(0,str(HERE))
from pub_splice import M
def one(job):
    eid,ag=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity,engine
    r=json.load(open(f"rlive3/{eid}.json")); A=r["acts"]; s=r["seat"]; o=1-s
    me=fidelity.make_agent(f"sub:{HERE}/agents/{ag}_main.py"); k=engine.load_kagsim(); g=k.Game(seed=r["seed"]); t=1
    while not engine._val(g.done) and t<len(A):
        a=[None,None]; a[s]=me(g.observe(s)); a[o]=A[t][o] or {}; g.step(a[0],a[1]); t+=1
    return eid,ag,float(g.reward(s)-g.reward(o))
if __name__=="__main__":
    AG=sys.argv[1].split(","); IDX=json.load(open("online_games.json"))
    E=[e for e,v in IDX.items() if v["ver"]==(sys.argv[2] if len(sys.argv)>2 else "v55b")]
    with ProcessPoolExecutor(8) as ex: R=list(ex.map(one,[(e,a) for e in E for a in AG]))
    D={}
    for e,a,d in R: D.setdefault(e,{})[a]=d
    for e in sorted(E,key=lambda e:IDX[e]["d"]):
        print(e,IDX[e]["opp_team"][:14].ljust(14),f"线上{IDX[e]['d']:+8.0f}"," ".join(f"{a}:{D[e][a]:+8.0f}" for a in AG))
    for a in AG: print(a,"胜",sum(D[e][a]>0 for e in E),"/",len(E),"均",round(sum(D[e][a] for e in E)/len(E)))
