"""盲带(不识别对手)质量:官方回放 1798 盘开环 + 双席位大种子 × 8 代表;与带识别的 r38c 对比。"""
import json, collections, os, sys
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
from official_eval import sim
W=int(os.environ.get("KAG_WORKERS","8")); AG=sys.argv[1] if len(sys.argv)>1 else "r38blind"; ENV=tuple(sys.argv[2].split(",")) if len(sys.argv)>2 else ()
OPPS=["me2965_28","guru28","harvest88","engineV3","rescue7","metav4","v52","fieldcraft29"]
if __name__=="__main__":
    rows=json.load(open("official_rows.json"))
    jobs=[(AG,"roff",r["eid"],r["seat"],ENV) for r in rows]
    with ProcessPoolExecutor(W) as ex: X=dict(ex.map(sim,jobs,chunksize=2))
    G=collections.defaultdict(lambda:[[],[]])
    for r,j in zip(rows,jobs):
        x=X.get(j)
        if not x: continue
        for g in (r["cls"],"合计"): G[g][0].append(x["d"]); G[g][1].append(r["d"])
    print(f"[官方回放 1798 盘] {AG}{ENV} vs r38c(带识别)")
    for c,(b,t) in sorted(G.items(),key=lambda kv:-len(kv[1][0])):
        print(f"   {c:10s} n={len(b):4d}  盲带 胜 {sum(x>0 for x in b):4d} ({sum(x>0 for x in b)/len(b):.0%}) 均{sum(b)/len(b):6.0f} | 识别 胜 {sum(x>0 for x in t):4d} ({sum(x>0 for x in t)/len(t):.0%}) 均{sum(t)/len(t):6.0f}",flush=True)
    json.dump({f"{k[2]}|{k[3]}":(v or {}).get("d") for k,v in X.items()},open(f"blind_rows_{AG}{'_'.join(ENV)}.json","w"))
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    jobs=[(AG,o,IDX[c][2],st,f"{o}|{c}|{st}",ENV) for o in OPPS for c in cells for st in (0,1)]
    with ProcessPoolExecutor(W) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    print(f"\n[双席位大种子 × 8 代表] {AG}{ENV}(r38c 带识别参照 842/1024)")
    tot=0
    for o in OPPS:
        d=[R.get(f"{o}|{c}|{st}") for c in cells for st in (0,1)]; d=[x for x in d if x is not None]; tot+=sum(x>0 for x in d)
        print(f"   {o:12s} {sum(x>0 for x in d):3d}/{len(d)} ({sum(x>0 for x in d)/len(d):.0%}) 均{sum(d)/len(d):6.0f}",flush=True)
    print(f"   合计 {tot}/1024 ({tot/1024:.0%})")
