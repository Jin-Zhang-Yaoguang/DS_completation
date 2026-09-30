import json, sys
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
if __name__=="__main__":
    agent=sys.argv[1]; env=tuple(x for x in sys.argv[2].split(";") if x)
    G=json.load(open("online_games.json")); R=json.load(open("cf_matrix.json"))
    jobs=[(agent,"rlive3",e,v["seat"],env) for e,v in G.items()]
    with ProcessPoolExecutor(8) as ex: X={j[2]:(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=2)}
    b=[R.get(f"v54r38f|{e}") for e in G]; a=[X.get(e) for e in G]
    P=[(p,q) for p,q in zip(a,b) if p is not None and q is not None]
    print(f"线上 322 局反事实: {agent}{env} 胜 {sum(p>0 for p,_ in P)}/{len(P)} 均差 {sum(p for p,_ in P)/len(P):.0f} | r38f 胜 {sum(q>0 for _,q in P)} 均差 {sum(q for _,q in P)/len(P):.0f} | 翻盘 +{sum(1 for p,q in P if p>0>=q)} −{sum(1 for p,q in P if q>0>=p)}")
