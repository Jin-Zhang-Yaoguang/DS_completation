import json, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    IDX=json.load(open("combo_index6.json"))["v54"]; pick=json.load(open("milk34_pick.json"))
    for seat in (0,1):
        for opp in ("guru28","me2965_28"):
            j0=[];j1=[]
            for c,(cut,r) in pick.items():
                for i in range(18,22):
                    if i>=len(IDX[c]): continue
                    sd=IDX[c][i]; j0.append(("v54r34",opp,sd,seat,f"{c}#{sd}",())); j1.append(("v54r35",opp,sd,seat,f"{c}#{sd}",()))
            with ProcessPoolExecutor(7) as ex: d0=dict(ex.map(be.one,j0,chunksize=4)); d1=dict(ex.map(be.one,j1,chunksize=4))
            print(f"  席位{seat} vs {opp}: r34 {sum(1 for v in d0.values() if v and v>0)}/{len(j0)} → r35 {sum(1 for v in d1.values() if v and v>0)}/{len(j1)}",flush=True)
    # 真实棋盘按席位拆分
    B=json.load(open("boards_ng_milk.json"))
    for opp in ("me2965_28",):
        a=be.run(B,"v54r34",opp); b=be.run(B,"v54r35",opp)
        for seat in (0,1):
            S=[x for x in B if x["seat"]==seat]
            print(f"  真实棋盘 席位{seat}({len(S)}盘) vs {opp}: r34 {sum(1 for x in S if (a.get(x['eid']) or 0)>0)} → r35 {sum(1 for x in S if (b.get(x['eid']) or 0)>0)}",flush=True)
