"""完整回归门控:r34(线上最好)vs r36 vs r38c。
A 大种子:64 组合 × 1 种子 × 8 个本地最强代表;B 官方回放开环:600 盘全人群;C 直接对打 r38c vs r34 128 局。"""
import json, random, collections, os
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
from official_eval import sim
VERS=["v54r34","v54r36","v54r38c"]
OPPS=["me2965_28","guru28","harvest88","engineV3","rescue7","metav4","v52","fieldcraft29"]
W=int(os.environ.get("KAG_WORKERS","8"))
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    # A
    jobs=[(v,o,IDX[c][2],hash(c)%2,f"{v}|{o}|{c}",()) for v in VERS for o in OPPS for c in cells]
    with ProcessPoolExecutor(W) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    print("[A 大种子 vs 本地最强代表] 胜/64 (均差)",flush=True)
    print("   "+f"{'代表':12s}"+"".join(f"{v[3:]:>18s}" for v in VERS))
    tot=collections.Counter(); tod=collections.Counter()
    for o in OPPS:
        line=f"   {o:12s}"
        for v in VERS:
            d=[R.get(f"{v}|{o}|{c}") for c in cells]; d=[x for x in d if x is not None]
            w=sum(x>0 for x in d); tot[v]+=w; tod[v]+=sum(d)
            line+=f"{w:>8d}/{len(d)} ({sum(d)/max(1,len(d)):6.0f})"
        print(line,flush=True)
    print("   合计        "+"".join(f"{tot[v]:>12d} 均{tod[v]/(64*len(OPPS)):6.0f}" for v in VERS),flush=True)
    # B
    rows=json.load(open("official_rows.json")); random.seed(7); S=random.sample(rows,600)
    jobs=[(v,"roff",r["eid"],r["seat"],()) for v in ("v54r34","v54r36") for r in S]
    with ProcessPoolExecutor(W) as ex: X=dict(ex.map(sim,jobs,chunksize=2))
    print("\n[B 官方回放开环 600 盘,按类] 胜 (均差)",flush=True)
    G=collections.defaultdict(lambda:collections.defaultdict(list))
    for r in S:
        G[r["cls"]]["v54r38c"].append(r["d"]); G["合计"]["v54r38c"].append(r["d"])
        for v in ("v54r34","v54r36"):
            x=X.get((v,"roff",r["eid"],r["seat"],()))
            if x: G[r["cls"]][v].append(x["d"]); G["合计"][v].append(x["d"])
    for c,g in sorted(G.items(),key=lambda kv:-len(kv[1]["v54r38c"])):
        print(f"   {c:10s} n={len(g['v54r38c']):3d} "+"  ".join(f"{v[3:]}: {sum(x>0 for x in g[v]):3d} ({sum(g[v])/max(1,len(g[v])):6.0f})" for v in VERS),flush=True)
    # C
    jobs=[("v54r38c","v54r34",IDX[c][i],i%2,f"{c}#{i}",()) for c in cells for i in (0,1)]
    import pub_splice; pub_splice.OPP["v54r34"]=str(be.HERE/"agents/v54r34_main.py")
    with ProcessPoolExecutor(W) as ex: Y=[d for _,d in ex.map(be.one,jobs,chunksize=2) if d is not None]
    print(f"\n[C 直接对打] r38c vs r34: r38c 胜 {sum(d>0 for d in Y)}/{len(Y)} 均差 {sum(Y)/max(1,len(Y)):.0f}",flush=True)
