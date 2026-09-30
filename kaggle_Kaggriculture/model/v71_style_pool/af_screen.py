"""动物优先开局:t144 统一改带筛选。样本=官方回放+我方线上中的动物优先开局对手棋盘(对手实录开环),按 eid 分半 A 选 B 验。"""
import json, hashlib, collections
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
ROUTES=[0,1,3,9,100,103,105,107,110,112,115,118,120,124,126]
if __name__=="__main__":
    X=json.load(open("style_feats.json"))
    B=[(("roff" if x["src"]=="官方" else "rlive3"),x["eid"],1-x["opp_seat"]) for x in X if x["key"][1] in (9990,9991,9992) and x["key"][0]<900]
    half=lambda e:"A" if int(hashlib.md5(str(e).encode()).hexdigest(),16)%2==0 else "B"
    print("动物优先开局棋盘",len(B),"A",sum(half(e)=="A" for _,e,_ in B),flush=True)
    arms=[("现状",())]+[(f"t144带{r}",(f"KAG_CUT144={r}",)) for r in ROUTES]
    jobs=[("r38gaf",src,e,seat,env) for name,env in arms for src,e,seat in B]
    with ProcessPoolExecutor(8) as ex: R={(j[4],j[2]):(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=2)}
    for part in ("A","B","全部"):
        print(f"[{part} 半]")
        for name,env in arms:
            d=[R.get((env,e)) for _,e,_ in B if part=="全部" or half(e)==part]; d=[v for v in d if v is not None]
            print(f"   {name:9s} 胜 {sum(v>0 for v in d):3d}/{len(d)}  均差 {sum(d)/max(1,len(d)):7.0f}",flush=True)
