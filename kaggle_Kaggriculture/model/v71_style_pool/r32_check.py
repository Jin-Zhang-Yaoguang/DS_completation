import json, glob, hashlib
import board_eval2 as be
from counter_select import half
if __name__=="__main__":
    comp={}
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    pick=json.load(open("counter_pick.json"))
    R=[x for x in json.load(open("boards_recent.json")) if x.get("seed") is not None and (x["key"],x["lin"]) in (("1042.0","main"),("1042.0","cha"))]
    print("近期 56 盘 vs me2965_28: r31 14/56(已测) → r32", sum(1 for d in be.run(R,"v54r32","me2965_28").values() if d and d>0),"/",len(R),flush=True)
    seen=set(); B=[]
    for fn in ("boards_recent.json","boards_all.json"):
        for x in json.load(open(fn)):
            if x.get("seed") is None or (x["key"],x["lin"])!=("1042.0","main") or x["eid"] in seen or x["eid"] not in comp: continue
            seen.add(x["eid"]); c="|".join((comp[x["eid"]].get("shops") or [])[:2])
            if half(x["eid"])=="B" and c in pick: B.append(x)
    for opp in ("herdsafe","shepledger"):
        a=be.run(B,"v54r31",opp); b=be.run(B,"v54r32",opp)
        print(f"护栏(老人群) vs {opp}: r31 {sum(1 for d in a.values() if d and d>0)}/{len(B)} → r32 {sum(1 for d in b.values() if d and d>0)}/{len(B)}",flush=True)
