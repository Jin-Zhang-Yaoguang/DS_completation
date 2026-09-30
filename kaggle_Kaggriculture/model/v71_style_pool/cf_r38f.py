import json
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
if __name__=="__main__":
    G=json.load(open("online_games.json")); R=json.load(open("cf_matrix.json"))
    jobs=[("v54r38f","rlive3",e,v["seat"],()) for e,v in G.items()]
    with ProcessPoolExecutor(8) as ex: X={j[2]:(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=2)}
    for e,d in X.items(): R[f"v54r38f|{e}"]=d
    json.dump(R,open("cf_matrix.json","w"))
    for v in ("v54r34","v54r38c","v54r38e","v54r38f"):
        d=[R.get(f"{v}|{e}") for e in G]; d=[x for x in d if x is not None]
        print(f"   {v[3:]:5s} 胜 {sum(x>0 for x in d)}/{len(d)} 均差 {sum(d)/len(d):.0f}")
