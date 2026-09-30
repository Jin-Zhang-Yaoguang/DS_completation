import json, sys
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]
    jobs=[]
    for c in sorted(IDX):
        for i in (0,1): jobs.append((sys.argv[1],sys.argv[2],IDX[c][i],i%2,f"{c}#{i}",()))
    with ProcessPoolExecutor(8) as ex: r=list(ex.map(be.one,jobs,chunksize=2))
    d=[v for e,v in r if v is not None]
    print(f"{sys.argv[1]} vs {sys.argv[2]}: 胜 {sum(x>0 for x in d)}/{len(d)} 均差 {sum(d)/max(1,len(d)):.0f}",flush=True)
