import json, glob, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    m=json.load(open("meta_live.json")); H=json.load(open("rkey_head.json"))
    comp={}
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    KEYS={1040.0,1050.0,1051.0,1052.0,1055.0}
    B=[]
    for e,v in m.items():
        if e not in comp or not H.get(e,{}).get("rkey") or float(H[e]["rkey"][0]) not in KEYS: continue
        if (v.get("end") or "")<"2026-09-27T12": continue
        r=comp[e]; B.append(dict(eid=e,ver=v["ver"],seed=r["seed"],seat=r["seat"],d=v["me"]["reward"]-v["opp"]["reward"],key=float(H[e]["rkey"][0])))
    print("棋盘",len(B),collections.Counter(x["key"] for x in B),"线上胜",sum(x["d"]>0 for x in B))
    KM=("KAG_KEYMAP=1041:1039,1043:1039,1040:1042,1050:1042,1051:1042,1052:1042,1055:1042",)
    for opp in ("me2965_28","harvest29","fieldcraft29"):
        j0=[("v54r38",opp,x["seed"],x["seat"],x["eid"],()) for x in B]; j1=[("v54r38",opp,x["seed"],x["seat"],x["eid"],KM) for x in B]
        with ProcessPoolExecutor(8) as ex: r0=dict(ex.map(be.one,j0,chunksize=1)); r1=dict(ex.map(be.one,j1,chunksize=1))
        by=collections.defaultdict(lambda:[0,0,0])
        for x in B:
            a=by[x["key"]]; a[0]+=1; a[1]+=(r0.get(x["eid"]) or 0)>0; a[2]+=(r1.get(x["eid"]) or 0)>0
        print(f"  vs {opp:12s}: 现状 {sum(a[1] for a in by.values())} → 映射 {sum(a[2] for a in by.values())} /{len(B)}   分键 "+" ".join(f"{int(k)}:{a[1]}→{a[2]}/{a[0]}" for k,a in sorted(by.items())),flush=True)
