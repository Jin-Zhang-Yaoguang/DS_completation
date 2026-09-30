"""动物优先顶队 vs 固定路线型对手的实录局:用 r38g/r34 替换固定路线型一方(对手实录开环),看胜率是否接近原选手(16%)。"""
import json, glob, collections, sys
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
from review_fp import cls
TEAMS=["Luca","Aaweg","Planned Economy","Arjun Vinod","high frequency farming","Alan C52","daulettoibazar","pangzi233","DeeperNet","Vlas Veles","tine.sh agent"]
FIXED={"新版人群","cha谱系","rescue7系","metav4","K52"}
if __name__=="__main__":
    B=[]
    for f in glob.glob("roff_af/*.json"):
        r=json.load(open(f)); nm=r["names"]; M=r["money"]
        for p,n in enumerate(nm):
            if n not in TEAMS: continue
            o=1-p; sk=r["key2"][o]
            if not (sk[1] in (9990,9991,9992) and sk[0]<900): continue
            k=r["key2"][p]; lin="cha" if (M[92] and M[91] and M[92][o]-M[91][o]>50) else "main"
            oc=cls(float(round(k[0])),lin)
            if oc in FIXED: B.append((r["eid"],o,n,oc,(r["rewards"][o] or 0)-(r["rewards"][p] or 0)))
    print("动物优先顶队 vs 固定路线型 实录局",len(B),"原固定路线型选手胜",sum(x[4]>0 for x in B),flush=True)
    import os
    os.makedirs("roff_afx",exist_ok=True)
    for e,*_ in B:
        dst=f"roff_afx/{e}.json"
        if not os.path.exists(dst):
            r=json.load(open(f"roff_af/{e}.json")); json.dump(r,open(dst,"w"))
    VV=["v54r38g","v54r34"]
    jobs=[(a,"roff_afx",e,o,()) for e,o,*_ in B for a in VV]
    with ProcessPoolExecutor(8) as ex: R={(j[0],j[2]):(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=2)}
    for a in VV:
        d=[R.get((a,e)) for e,*_ in B]; d=[x for x in d if x is not None]
        print(f"   {a[3:]} 替换后 胜 {sum(x>0 for x in d)}/{len(d)} ({sum(x>0 for x in d)/max(1,len(d)):.0%}) 均差 {sum(d)/max(1,len(d)):.0f}")
    by=collections.defaultdict(lambda:[0,0,0])
    for e,o,n,oc,d0 in B:
        x=R.get(("v54r38g",e))
        if x is None: continue
        a=by[n]; a[0]+=1; a[1]+=x>0; a[2]+=d0>0
    print("   按目标队伍: 局 / r38g 胜 / 原选手胜")
    for n,a in sorted(by.items(),key=lambda kv:-kv[1][0]): print(f"      {n[:24]:24s} {a[0]:3d} / {a[1]:3d} / {a[2]:3d}")
