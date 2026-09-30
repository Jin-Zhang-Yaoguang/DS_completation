"""谱系代表搜索:在该谱系的真实棋盘上,实际参赛版本 vs 候选方案,看模拟胜负与线上真实一致率。"""
import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
from board_eval import one
from pub_splice import OPP
if __name__=="__main__":
    groups=[tuple(g.split("/")) for g in sys.argv[1].split(";")]; cands=sys.argv[2].split(",")
    import os; rows=[x for x in json.load(open(HERE/os.environ.get("RS_FILE","scan_live_rows.json"))) if x.get("seed") is not None and (x["key"],x["lin"]) in groups]
    jobs=[(x["ver"],c,x["seed"],x["seat"],x["eid"]) for x in rows for c in cands]
    print("棋盘",len(rows),"任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    real={x["eid"]:(x["d"]>0,(x["key"],x["lin"])) for x in rows}
    A=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0]))
    for (v,c,s,seat,e),(_,_,d) in zip(jobs,res):
        if d is None: continue
        w,g=real[e]; a=A[g][c]; a[0]+=(d>0)==w; a[1]+=1
    for g in A:
        print(f"== {g}  (线上实际胜 {sum(1 for x in rows if (x['key'],x['lin'])==g and x['d']>0)}/{sum(1 for x in rows if (x['key'],x['lin'])==g)})")
        for c,a in sorted(A[g].items(),key=lambda kv:-kv[1][0]/max(1,kv[1][1])): print(f"   {c:14s} 一致 {a[0]}/{a[1]} ({a[0]/max(1,a[1]):.0%})")
