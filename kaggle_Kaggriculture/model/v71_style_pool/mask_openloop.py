"""伪装开局的代价来源:对手用官方回放里固定路线型选手的实录(开环,不会对我们反应),比较 r38g 与 r38m2。"""
import json, random
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
if __name__=="__main__":
    rows=[r for r in json.load(open("official_rows.json")) if r["cls"] in ("新版人群","cha谱系","rescue7系")]
    random.seed(3); S=random.sample(rows,160)
    jobs=[(a,"roff",r["eid"],r["seat"],()) for r in S for a in ("v54r38g","r38m2","v54r38m")]
    with ProcessPoolExecutor(8) as ex: R={(j[0],j[2],j[3]):(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=2)}
    for a in ("v54r38g","r38m2","v54r38m"):
        d=[R.get((a,r["eid"],r["seat"])) for r in S]; d=[x for x in d if x is not None]
        print(f"   {a:8s} vs 固定路线型实录(不反应) 胜 {sum(x>0 for x in d)}/{len(d)} 均差 {sum(d)/max(1,len(d)):.0f}")
