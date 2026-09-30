import json, glob
import board_eval2 as be
if __name__=="__main__":
    pick=json.load(open("milkbig_pick.json"))
    comp={}
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    B=[x for x in json.load(open("boards_ng_milk.json")) if "|".join((comp[x["eid"]].get("shops") or [])[:2]) in pick]
    for opp in ("me2965_28","harvest29"):
        a=be.run(B,"v54r34",opp); b=be.run(B,"v54r36",opp)
        print(f"真实棋盘(受影响 {len(B)} 盘) vs {opp}: r34 {sum(1 for v in a.values() if v and v>0)} → r36 {sum(1 for v in b.values() if v and v>0)}",flush=True)
    lab,_=json.load(open("bigseed.json"))
    C=[dict(seed=s,seat=i%2,eid=f"b{s}") for i,(s,l,r) in enumerate(lab) if r in pick]
    a=be.run(C,"v54r34","me2965_28"); b=be.run(C,"v54r36","me2965_28")
    print(f"另一批独立大种子({len(C)} 盘) vs me2965_28: r34 {sum(1 for v in a.values() if v and v>0)} → r36 {sum(1 for v in b.values() if v and v>0)}")
