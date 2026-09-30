import json, glob
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    IDX=json.load(open("combo_index6.json"))["v54"]; pick=json.load(open("milk34_pick.json"))
    j0=[];j1=[]
    for c in pick:
        for i in range(22,30):
            if i>=len(IDX[c]): continue
            sd=IDX[c][i]; seat=i%2
            j0.append(("v54r34","me2965_28",sd,seat,f"{c}#{sd}",())); j1.append(("v54r35","me2965_28",sd,seat,f"{c}#{sd}",()))
    with ProcessPoolExecutor(7) as ex: d0=dict(ex.map(be.one,j0,chunksize=4)); d1=dict(ex.map(be.one,j1,chunksize=4))
    print(f"新种子 idx22-29(席位交替) vs me2965_28: r34 {sum(1 for v in d0.values() if v and v>0)}/{len(j0)} → r35 {sum(1 for v in d1.values() if v and v>0)}/{len(j1)}",flush=True)
    comp={}
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    B=[x for x in json.load(open("boards_ng_milk.json")) if "|".join((comp[x["eid"]].get("shops") or [])[:2]) in pick]
    a=be.run(B,"v54r34","me2965_28"); b=be.run(B,"v54r35","me2965_28")
    print(f"真实棋盘(仅受影响组合 {len(B)} 盘) vs me2965_28: r34 {sum(1 for v in a.values() if v and v>0)} → r35 {sum(1 for v in b.values() if v and v>0)}")
