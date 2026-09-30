"""r38f 三项门控(全新数据):A idx18,19 双席位×5 代表;B 官方回放 1798 盘;C r38f vs r38e 双席位直接对打。"""
import json, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
from official_eval import sim
OPPS=["me2965_28","guru28","engineV3","rescue7","fieldcraft29"]; VV=["v54r38e","v54r38f"]
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    jobs=[(v,o,IDX[c][i],st,f"{v}|{o}|{c}|{i}|{st}",()) for v in VV for o in OPPS for c in cells for i in (18,19) for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    print("[A 样本外 idx18-19 双席位] 胜/256 (均差)")
    tot=collections.Counter()
    for o in OPPS:
        line=f"   {o:12s}"
        for v in VV:
            d=[x for k,x in R.items() if k.startswith(f"{v}|{o}|") and x is not None]; tot[v]+=sum(x>0 for x in d)
            line+=f"  {v[3:]}: {sum(x>0 for x in d):3d} ({sum(d)/max(1,len(d)):5.0f})"
        print(line,flush=True)
    print("   合计 "+"  ".join(f"{v[3:]}: {tot[v]}/1280" for v in VV),flush=True)
    rows=json.load(open("official_rows.json"))
    jobs=[(v,"roff",r["eid"],r["seat"],()) for v in VV for r in rows]
    with ProcessPoolExecutor(8) as ex: X={(j[0],j[2],j[3]):(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=2)}
    G=collections.defaultdict(lambda:collections.defaultdict(list))
    for r in rows:
        vals={v:X.get((v,r["eid"],r["seat"])) for v in VV}
        if None in vals.values(): continue
        for g in (r["cls"],"合计"):
            for v in VV: G[g][v].append(vals[v])
    print("\n[B 官方回放 1798 盘] 胜 (均差)")
    for c,g in sorted(G.items(),key=lambda kv:-len(kv[1]["v54r38e"])):
        a,b=g["v54r38e"],g["v54r38f"]
        print(f"   {c:10s} n={len(a):4d}  r38e: {sum(x>0 for x in a):4d} ({sum(a)/len(a):6.0f})  r38f: {sum(x>0 for x in b):4d} ({sum(b)/len(b):6.0f})  翻盘 +{sum(1 for p,q in zip(a,b) if q>0>=p)} −{sum(1 for p,q in zip(a,b) if p>0>=q)}",flush=True)
    jobs=[("v54r38f","v54r38e",IDX[c][i],st,f"{c}|{i}|{st}",()) for c in cells for i in (18,19) for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: Z=[d for _,d in ex.map(be.one,jobs,chunksize=2) if d is not None]
    print(f"\n[C 直接对打] r38f vs r38e {len(Z)} 局: 胜 {sum(x>0 for x in Z)} 平 {sum(x==0 for x in Z)} 负 {sum(x<0 for x in Z)} 均差 {sum(Z)/max(1,len(Z)):.0f}",flush=True)
