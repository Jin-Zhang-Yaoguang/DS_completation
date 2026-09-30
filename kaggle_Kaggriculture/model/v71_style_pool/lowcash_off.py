import json, collections
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
if __name__=="__main__":
    R=json.load(open("official_rows.json"))
    T=[r for r in R if r["cls"]=="其他低现金"]
    jobs=[("v54r38","roff",r["eid"],r["seat"],()) for r in T]
    with ProcessPoolExecutor(8) as ex: X=dict(ex.map(sim,jobs,chunksize=1))
    G=collections.defaultdict(list)
    for r,j in zip(T,jobs):
        q=(X.get(j) or {}).get("d")
        if q is None: continue
        g="小麦9990" if r["key"][1]==9990 else "其他"
        G[g].append((r["d"],q)); G["合计"].append((r["d"],q))
    for g,P in G.items():
        print(f"其他低现金[{g}] n={len(P)}: r38c(不触发) 胜 {sum(p>0 for p,_ in P)} 均 {sum(p for p,_ in P)/len(P):.0f} | r38(触发126) 胜 {sum(q>0 for _,q in P)} 均 {sum(q for _,q in P)/len(P):.0f}")
