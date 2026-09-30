import json, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
from review_fp import one as tone
if __name__=="__main__":
    B=json.load(open("boards_chavar.json"))
    for opp in ("TAPE","engineV3","cha22","tetsu16"):
        if opp=="TAPE":
            jobs=[(a,"TAPE",x["eid"],()) for x in B for a in ("v54r38c","v54r38d")]
            with ProcessPoolExecutor(8) as ex: R={(j[0],j[2]):d for j,d in ex.map(tone,jobs,chunksize=1)}
        else:
            jobs=[(a,opp,x["seed"],x["seat"],f"{a}|{x['eid']}",()) for x in B for a in ("v54r38c","v54r38d")]
            with ProcessPoolExecutor(8) as ex: R={tuple(e.split("|")):d for e,d in ex.map(be.one,jobs,chunksize=1)}
        for lvl,flt in (("全部",lambda x:True),("≥2000",lambda x:x["opp"]>=2000)):
            T=[x for x in B if flt(x) and R.get(("v54r38c",x["eid"])) is not None and R.get(("v54r38d",x["eid"])) is not None]
            a=[R[("v54r38c",x["eid"])] for x in T]; b=[R[("v54r38d",x["eid"])] for x in T]
            print(f"  vs {opp:9s} {lvl:5s} n={len(T):2d}  r38c 胜{sum(v>0 for v in a):3d} 均{sum(a)/len(T):7.0f} | r38d 胜{sum(v>0 for v in b):3d} 均{sum(b)/len(T):7.0f} | 翻盘 +{sum(1 for p,q in zip(a,b) if q>0>=p)} −{sum(1 for p,q in zip(a,b) if p>0>=q)}",flush=True)
