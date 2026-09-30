"""v55 候选样本外评估:idx20,21 双席位 × 对手;可选对照 agent。"""
import json, sys
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    AG=sys.argv[1].split(","); OPPS=sys.argv[2].split(","); IDXS=[int(x) for x in (sys.argv[3] if len(sys.argv)>3 else "20,21").split(",")]
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    jobs=[(a,o,IDX[c][i],st,f"{a}|{o}|{c}|{i}|{st}",()) for a in AG for o in OPPS for c in cells for i in IDXS for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    for o in OPPS:
        line=f"   vs {o:16s}"
        for a in AG:
            d=[v for k,v in R.items() if k.startswith(f"{a}|{o}|") and v is not None]
            line+=f"  {a}: {sum(x>0 for x in d):3d}/{len(d)} ({sum(x>0 for x in d)/max(1,len(d)):.0%}) 均{sum(d)/max(1,len(d)):7.0f}"
        print(line,flush=True)
    json.dump({k:v for k,v in R.items()},open("v55_eval_last.json","w"))
