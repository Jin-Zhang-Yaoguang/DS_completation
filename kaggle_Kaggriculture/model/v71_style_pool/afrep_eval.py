"""复刻代表强度:r38g 与本地代表 vs 三个固定带复刻(样本外 idx20,21 双席位 64 组合 = 256 局/对)。"""
import json
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    AG=["v54r38g","me2965_28","engineV3"]; OP=["afrep_deepernet","afrep_planned","afrep_arjun"]
    jobs=[(a,o,IDX[c][i],st,f"{a}|{o}|{c}|{i}|{st}",()) for a in AG for o in OP for c in cells for i in (20,21) for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    for o in OP:
        line=f"   对手 {o:16s}"
        for a in AG:
            d=[v for k,v in R.items() if k.startswith(f"{a}|{o}|") and v is not None]
            line+=f"  {a}: {sum(x>0 for x in d):3d}/{len(d)} ({sum(x>0 for x in d)/max(1,len(d)):.0%}) 均{sum(d)/max(1,len(d)):7.0f}"
        print(line,flush=True)
