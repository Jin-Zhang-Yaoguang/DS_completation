import json, collections
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
if __name__=="__main__":
    X=json.load(open("style_feats.json"))
    g=lambda x,t,k: (x["feats"].get(str(t)) or x["feats"].get(t) or {}).get(k,0)
    B=[(("roff" if x["src"]=="官方" else "rlive3"),x["eid"],1-x["opp_seat"]) for x in X if x["key"][1] in (9990,9991,9992) and x["key"][0]<900 and g(x,288,"land")<=2]
    arms=[("现状",())]+[(f"t288带{r}",(f"KAG_CUT288={r}",)) for r in (0,100,103,107)]+[(f"t432带{r}",(f"KAG_CUT432={r}",)) for r in (0,100)]
    jobs=[("r38gaf",s,e,st,env) for n,env in arms for s,e,st in B]
    with ProcessPoolExecutor(8) as ex: R={(j[4],j[2]):(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=2)}
    print("买地≤2 的动物优先开局棋盘",len(B))
    for n,env in arms:
        d=[R.get((env,e)) for _,e,_ in B]; d=[v for v in d if v is not None]
        print(f"   {n:9s} 胜 {sum(v>0 for v in d):3d}/{len(d)} 均差 {sum(d)/max(1,len(d)):7.0f}",flush=True)
