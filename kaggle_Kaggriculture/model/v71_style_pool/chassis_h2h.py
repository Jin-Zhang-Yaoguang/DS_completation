"""底盘是否过期:r38g vs 最新公开方案,样本外 idx20 双席位 64 组合 = 128 局/对手。"""
import json
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
OPPS=["harvest88","gurutop2","hyb2965","shep29","wheatseller","ttv1","fieldcraft29","tetsu16","me2965_28","engineV3"]
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    jobs=[("v54r38g",o,IDX[c][20],st,f"{o}|{c}|{st}",()) for o in OPPS for c in cells for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    for o in OPPS:
        d=[v for k,v in R.items() if k.startswith(o+"|") and v is not None]
        print(f"   r38g vs {o:12s} 胜 {sum(x>0 for x in d):3d}/{len(d)} ({sum(x>0 for x in d)/max(1,len(d)):.0%})  均差 {sum(d)/max(1,len(d)):7.0f}",flush=True)
