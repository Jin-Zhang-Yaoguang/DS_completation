import json,glob
from concurrent.futures import ProcessPoolExecutor
import board_eval
if __name__=="__main__":
    comp={}
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    rows=[x for x in json.load(open("scan_live_rows.json")) if (x["key"],x["lin"])==("1042.0","cha") and x.get("seed") is not None]
    flip={"BRUNCH_SPOT|PET_CAFE","ICE_CREAM_SHOP|SMOOTHIE_SHOP","ICE_CREAM_SHOP|PIZZA_SHOP"}
    tgt=[x for x in rows if "|".join((comp[x["eid"]].get("shops") or [])[:2]) in flip]
    jobs=[("r30","engineV3",x["seed"],x["seat"],x["eid"]) for x in tgt]
    with ProcessPoolExecutor(4) as ex: out=list(ex.map(board_eval.one,jobs))
    base={e:d for v,e,d in json.load(open("board_eval_r29.json"))}
    print("r30 在 3 格棋盘上:",sum((d or 0)>0 for _,_,d in out),"/",len(out),"(r29:",sum(base[x['eid']]>0 for x in tgt),")")
