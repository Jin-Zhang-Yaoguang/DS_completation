"""cha 变体(1039/1040/1041/1043 键 + t92 信号)的最近 5 天真实棋盘 + 代表保真。"""
import json, glob, datetime, os
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    m=json.load(open("meta_live.json")); H=json.load(open("rkey_head.json"))
    SINCE=(datetime.datetime.now(datetime.UTC)-datetime.timedelta(days=5)).strftime("%Y-%m-%dT%H")
    B=[]
    for e,v in m.items():
        k=(H.get(e) or {}).get("rkey"); f=f"rlive3/{e}.json"
        if not k or float(k[0]) not in (1039.0,1040.0,1041.0,1043.0) or (v.get("end") or "")<SINCE or not os.path.exists(f) or not v.get("opp"): continue
        r=json.load(open(f)); o=1-r["seat"]; M=r["money"]
        if not (M[92] and M[91] and M[92][o]-M[91][o]>50): continue
        B.append(dict(eid=e,ver=("r38" if v["ver"]=="r38b" else v["ver"]),seed=r["seed"],seat=r["seat"],d=v["me"]["reward"]-v["opp"]["reward"],opp=v["opp"]["initialScore"],key=float(k[0]),shops=(r.get("shops") or [])[:2],team=v.get("opp_team")))
    json.dump(B,open("boards_chavar.json","w"),ensure_ascii=False)
    print("cha 变体棋盘",len(B),"线上胜",sum(x["d"]>0 for x in B),"≥2000:",sum(x["opp"]>=2000 for x in B),flush=True)
    for rep in ("engineV3","tetsu16","cha22","demand28","me2965_28"):
        jobs=[(f"v54{x['ver']}",rep,x["seed"],x["seat"],x["eid"],()) for x in B]
        with ProcessPoolExecutor(8) as ex: R=dict(ex.map(be.one,jobs,chunksize=1))
        ok=sum(1 for x in B if R.get(x["eid"]) is not None and (R[x["eid"]]>0)==(x["d"]>0)); lw=sum(1 for x in B if x["d"]<0 and (R.get(x["eid"]) or 1)<0)
        print(f"  代表 {rep:10s} 一致 {ok}/{len(B)} ({ok/max(1,len(B)):.0%}) 线上败局复现 {lw}/{sum(x['d']<0 for x in B)}",flush=True)
