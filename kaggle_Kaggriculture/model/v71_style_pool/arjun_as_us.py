"""把 Arjun 固定带复刻当作我方:A 样本外 idx20,21 双席位 × 多对手;B 官方回放全量开环。对照 r38g。"""
import json, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
from official_eval import sim
OPPS=["me2965_28","guru28","harvest88","engineV3","rescue7","metav4","v52","fieldcraft29","v54r38g","afrep_deepernet","afrep_planned"]
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    jobs=[("afrep_arjun",o,IDX[c][i],st,f"{o}|{c}|{i}|{st}",()) for o in OPPS for c in cells for i in (20,21) for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    print("[A Arjun 固定带作为我方,样本外双席位] 胜/256 (均差)")
    for o in OPPS:
        d=[v for k,v in R.items() if k.startswith(o+"|") and v is not None]
        print(f"   vs {o:16s} {sum(x>0 for x in d):3d}/{len(d)} ({sum(x>0 for x in d)/max(1,len(d)):.0%}) 均{sum(d)/max(1,len(d)):7.0f}",flush=True)
    rows=json.load(open("official_rows.json"))
    jobs=[("afrep_arjun","roff",r["eid"],r["seat"],()) for r in rows]
    with ProcessPoolExecutor(8) as ex: X={(j[2],j[3]):(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=2)}
    G=collections.defaultdict(lambda:[[],[]])
    for r in rows:
        a=X.get((r["eid"],r["seat"]))
        if a is None: continue
        for g in (r["cls"],"合计"): G[g][0].append(a); G[g][1].append(r["d"])
    print("\n[B 官方回放 1798 盘开环] Arjun 固定带 vs r38c(当时的我方)")
    for c,(a,b) in sorted(G.items(),key=lambda kv:-len(kv[1][0])):
        print(f"   {c:10s} n={len(a):4d}  Arjun 胜 {sum(x>0 for x in a):4d} ({sum(x>0 for x in a)/len(a):.0%}) 均{sum(a)/len(a):7.0f} | r38c 胜 {sum(x>0 for x in b):4d} ({sum(x>0 for x in b)/len(b):.0%}) 均{sum(b)/len(b):7.0f}",flush=True)
