import json, glob, collections
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
from review_fp import cls
if __name__=="__main__":
    B=[]
    for f in glob.glob("roff_afx/*.json"):
        r=json.load(open(f))
        for s in (0,1):
            k2=r["key2"][1-s]
            if k2[1] in (9990,9991,9992) and k2[0]<900: B.append((r["eid"],1-s))
    B=list(dict.fromkeys(B))
    jobs=[(a,"roff_afx",e,me,()) for e,me in B for a in ("v54r38g","v54r38n")]
    with ProcessPoolExecutor(8) as ex: R={(j[0],j[2],j[3]):(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=2)}
    P=[(R.get(("v54r38n",e,m)),R.get(("v54r38g",e,m))) for e,m in B]; P=[p for p in P if None not in p]
    print(f"顶队针对固定路线型的实录 {len(P)} 局: r38n 胜 {sum(a>0 for a,_ in P)} 均差 {sum(a for a,_ in P)/len(P):.0f} | r38g 胜 {sum(b>0 for _,b in P)} 均差 {sum(b for _,b in P)/len(P):.0f} | 结果完全相同 {sum(a==b for a,b in P)}")
    # 误触发:我方线上对局中,对手第1步现金落入触发档的比例(按对手人群)
    G=json.load(open("online_games.json")); C=collections.defaultdict(lambda:[0,0])
    for e,v in G.items():
        try:
            r=json.load(open(f"rlive3/{e}.json")); om=r["money"][1][1-r["seat"]]
        except Exception: continue
        trig=(2450<=om<2500) or (2625<=om<2675) or (950<=om<1000)
        c=cls(float(round(v["key"][0])),v["lin"]) if v.get("key") else "?"
        C[c][0]+=1; C[c][1]+=trig
    print("我方线上对局 触发率(按对手人群):",{c:f"{a[1]}/{a[0]}" for c,a in sorted(C.items(),key=lambda kv:-kv[1][0])})
