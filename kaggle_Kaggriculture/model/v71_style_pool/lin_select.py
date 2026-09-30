"""谱系专属选带:单谱系对手 × 64 组合 × 53 臂 × 多种子。
用法: python lin_select.py <tag> <opp> <种子序号,逗号>  → lin_select_<tag>.json"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
from pub_splice import one, IDX, ARMS
if __name__=="__main__":
    tag,opp=sys.argv[1],sys.argv[2]; sis=[int(x) for x in sys.argv[3].split(",")]
    jobs=[]
    for c,s in sorted(IDX.items()):
        seeds=sorted({s[min(i,len(s)-1)] for i in sis})
        for sd in seeds:
            for cut,rid in ARMS: jobs.append((c,opp,sd,cut,rid))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/f"lin_select_{tag}.json","w")); print("完成")
