"""cha 谱系应对策略三选一:现状(r38e) / 关 cha 格 / 对 cha 盲带。官方 cha 棋盘 + 我方线上 cha 对局(开环) + 双席位大种子 vs engineV3、cha22。"""
import json, collections, os
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
from official_eval import sim
from review_fp import cls
W=8
ARMS=[("现状",()),("关cha格",("KAG_CUTOFF=CHA",)),("cha盲带",("KAG_CHABLIND=1",))]
if __name__=="__main__":
    rows=[r for r in json.load(open("official_rows.json")) if r["cls"]=="cha谱系"]
    G=json.load(open("online_games.json"))
    own=[(e,v) for e,v in G.items() if v.get("key") and cls(float(round(v["key"][0])),v["lin"])=="cha谱系"]
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    for title,mk in (("官方回放 cha 棋盘",lambda env:[("r38eabl","roff",r["eid"],r["seat"],env) for r in rows]),
                     ("我方线上 cha 对局",lambda env:[("r38eabl","rlive3",e,v["seat"],env) for e,v in own])):
        out=[]
        for name,env in ARMS:
            with ProcessPoolExecutor(W) as ex: X=[(x or {}).get("d") for _,x in ex.map(sim,mk(env),chunksize=2)]
            X=[x for x in X if x is not None]; out.append(f"{name}: {sum(x>0 for x in X)}/{len(X)} 均{sum(X)/max(1,len(X)):6.0f}")
        print(f"[{title}] "+"  |  ".join(out),flush=True)
    for opp in ("engineV3","cha22"):
        out=[]
        for name,env in ARMS:
            jobs=[("r38eabl",opp,IDX[c][i],st,f"{c}|{i}|{st}",env) for c in cells for i in (0,1) for st in (0,1)]
            with ProcessPoolExecutor(W) as ex: X=[d for _,d in ex.map(be.one,jobs,chunksize=4) if d is not None]
            out.append(f"{name}: {sum(x>0 for x in X)}/{len(X)} 均{sum(X)/max(1,len(X)):6.0f}")
        print(f"[双席位大种子 vs {opp}] "+"  |  ".join(out),flush=True)
