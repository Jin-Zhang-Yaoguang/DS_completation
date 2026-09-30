"""顶队(榜分≥2600)整局动作经底盘执行:在其原种子原席位,对 3 个代表;对照 r38g 同条件。"""
import json, glob, csv, sys, os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    LB={}
    for f in glob.glob(sys.argv[1]+"/*.csv"):
        for r in csv.DictReader(open(f,encoding="utf-8-sig")): LB[r["TeamName"]]=float(r["Score"])
    rows=json.load(open("official_rows.json"))
    # 顶队玩家 = 被 r38c 顶替席位的对面(对手),其席位 = 1-seat
    top=[r for r in rows if LB.get(r["team"],0)>=2600]
    print("顶队实录局",len(top),"队伍",len({r['team'] for r in top}),flush=True)
    OPPS=["me2965_28","engineV3","rescue7"]
    seedof={r["eid"]:json.load(open(f"roff/{r['eid']}.json"))["seed"] for r in top}
    jobs=[]
    for r in top:
        ts=1-r["seat"]
        for o in OPPS:
            jobs.append(("r38tape",o,seedof[r["eid"]],ts,f"T|{o}|{r['eid']}",(f"KAG_TAPE={r['eid']}:{ts}",)))
            jobs.append(("v54r38g",o,seedof[r["eid"]],ts,f"G|{o}|{r['eid']}",()))
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(be.one,jobs,chunksize=2))
    for o in OPPS:
        for tag,name in (("T","顶队动作带+底盘"),("G","r38g")):
            d=[v for k,v in R.items() if k.startswith(f"{tag}|{o}|") and v is not None]
            print(f"   {name:14s} vs {o:10s} 胜 {sum(x>0 for x in d):3d}/{len(d)} ({sum(x>0 for x in d)/max(1,len(d)):.0%}) 均差 {sum(d)/max(1,len(d)):7.0f}",flush=True)
