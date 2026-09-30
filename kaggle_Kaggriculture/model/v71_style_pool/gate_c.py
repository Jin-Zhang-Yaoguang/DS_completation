import json
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    jobs=[("v54r38c","v54r34",IDX[c][i],i%2,f"{c}#{i}",()) for c in cells for i in (0,1)]
    with ProcessPoolExecutor(8) as ex: Y=[d for _,d in ex.map(be.one,jobs,chunksize=2) if d is not None]
    print(f"r38c vs r34 ({len(Y)} 局): 胜 {sum(d>0 for d in Y)} 平 {sum(d==0 for d in Y)} 负 {sum(d<0 for d in Y)} 均差 {sum(Y)/len(Y):.0f}")
