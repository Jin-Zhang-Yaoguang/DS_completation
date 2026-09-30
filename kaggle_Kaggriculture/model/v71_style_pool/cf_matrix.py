"""反事实矩阵:全部线上对局 × 版本(对手按实录开环)。检验:实际版本复现线上;同棋盘版本对比;按分段/人群/实际上场版本拆分。"""
import json, glob, csv, collections, sys, os
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
from review_fp import cls
VERS=["v54r34","v54r36","v54r38c","v54r38e"]
ACT={"r34":"v54r34","r36":"v54r36","r38":"v54r38","r38b":"v54r38","r38c":"v54r38c"}
if __name__=="__main__":
    LB={}
    for f in glob.glob(sys.argv[1]+"/*.csv"):
        for r in csv.DictReader(open(f,encoding="utf-8-sig")): LB[r["TeamName"]]=float(r["Score"])
    G=json.load(open("online_games.json"))
    jobs=[]
    for e,v in G.items():
        for a in set(VERS+[ACT[v["ver"]]]): jobs.append((a,"rlive3",e,v["seat"],()))
    with ProcessPoolExecutor(8) as ex: R={(j[0],j[2]):(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=2)}
    json.dump({f"{a}|{e}":d for (a,e),d in R.items()},open("cf_matrix.json","w"))
    ok=sum(1 for e,v in G.items() if R.get((ACT[v["ver"]],e))==v["d"]); print(f"[检查] 实际上场版本开环复现线上奖励差:{ok}/{len(G)} 完全一致",flush=True)
    band=lambda s:"<1500" if s<1500 else "1500-2000" if s<2000 else "2000-2400" if s<2400 else "≥2400"
    def table(title,keyf):
        T=collections.defaultdict(lambda:collections.defaultdict(list))
        for e,v in G.items():
            k=keyf(e,v)
            for a in VERS:
                d=R.get((a,e))
                if d is not None: T[k][a].append(d); T["合计"][a].append(d)
            T[k]["线上"].append(v["d"]); T["合计"]["线上"].append(v["d"])
        print(f"\n[{title}] 胜数/局 (均差)")
        for k,t in sorted(T.items(),key=lambda kv:(kv[0]!="合计",kv[0])):
            n=len(t["线上"])
            print(f"   {str(k):14s} n={n:3d} 线上 {sum(x>0 for x in t['线上']):3d}  "+"  ".join(f"{a[3:]}: {sum(x>0 for x in t[a]):3d} ({sum(t[a])/max(1,len(t[a])):6.0f})" for a in VERS))
    table("按对手当前榜分段",lambda e,v: band(LB.get(v["opp_team"],0)))
    table("按对手人群",lambda e,v: cls(float(round(v["key"][0])),v["lin"]) if v.get("key") else "?")
    table("按实际上场版本(该版本行=精确,其余=开环近似)",lambda e,v: v["ver"])
    # r38c 实际输局:其他版本能否翻盘
    L=[(e,v) for e,v in G.items() if v["ver"]=="r38c" and v["d"]<0]
    print(f"\n[r38c 线上 {len(L)} 局败局] 各版本开环能赢的局数:"+"  ".join(f"{a[3:]} {sum(1 for e,_ in L if (R.get((a,e)) or 0)>0)}" for a in VERS))
    for e,v in sorted(L,key=lambda ev:ev[1]["end"]):
        print(f"   {v['end'][5:16]} {v['opp_team'][:16]:16s} 榜分 {LB.get(v['opp_team'],0):6.0f} {cls(float(round(v['key'][0])),v['lin']):8s} 线上 {v['d']:7.0f} | "+" ".join(f"{a[3:]}:{R.get((a,e)) or 0:7.0f}" for a in VERS))
