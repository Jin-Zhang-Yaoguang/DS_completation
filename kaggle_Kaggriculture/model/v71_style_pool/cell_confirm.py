"""格值确认轮:给定 {格:(cut,rid)} 表 × {默认, 候选} × 对手面板 × 指定种子序号。
用法: python cell_confirm.py <表json> <opp,opp> <种子序号,逗号> <tag>"""
import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
from pub_splice import one, IDX
if __name__=="__main__":
    tab=json.load(open(HERE/sys.argv[1])); opps=sys.argv[2].split(","); sis=[int(x) for x in sys.argv[3].split(",")]; tag=sys.argv[4]
    jobs=[]
    for c,(cut,rid) in tab.items():
        s=IDX[c]; seeds=sorted({s[i] for i in sis if i<len(s)})
        for sd in seeds:
            for o in opps:
                for arm in ((None,-1),(cut,rid)): jobs.append((c,o,sd,arm[0],arm[1]))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/f"confirm_{tag}.json","w"))
    A=collections.defaultdict(lambda:[[0,0,0.0],[0,0,0.0]]); O=collections.defaultdict(lambda:[[0,0],[0,0]])
    for c,o,s,cut,rid,m in res:
        if m is None: continue
        i=0 if cut is None else 1; a=A[c][i]; a[0]+=m>0; a[1]+=1; a[2]+=m; O[o][i][0]+=m>0; O[o][i][1]+=1
    keep={}
    for c,(d,n) in sorted(A.items()):
        good=n[0]>=d[0] and n[2]>d[2]
        if good: keep[c]=tab[c]
        print(f"[{'过' if good else '弃'}] {c:32s} 默认 {d[0]}/{d[1]}({d[2]/max(1,d[1]):+6.0f}) 候选{tuple(tab[c])} {n[0]}/{n[1]}({n[2]/max(1,n[1]):+6.0f})")
    print("分对手 默认→候选:",{o:f"{a[0][0]}/{a[0][1]}→{a[1][0]}/{a[1][1]}" for o,a in O.items()})
    print("通过",len(keep),"/",len(tab)); json.dump(keep,open(HERE/f"confirm_{tag}_keep.json","w"))
