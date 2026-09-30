"""混合面板选带留出:选中格 × {默认, 选中带} × 面板 × 新种子(combo_index3 序号 3,4;与选带种子重复则跳过)。"""
import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
from pub_splice import one, IDX
from mix_select import PANEL
if __name__=="__main__":
    key=sys.argv[1]; sel=json.load(open(HERE/f"mix_sel_{key}.json")); jobs=[]
    for c,(cut,rid) in sel.items():
        s=IDX[c]; used=s[min(2,len(s)-1)]
        for si in (3,4,5):
            if si>=len(s) or s[si]==used: continue
            for o in PANEL[key]:
                for arm in ((None,-1),(cut,rid)): jobs.append((c,o,s[si],arm[0],arm[1]))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/f"mix_holdout_{key}.json","w"))
    A=collections.defaultdict(lambda:[[0,0,0.0],[0,0,0.0]]); O=collections.defaultdict(lambda:[[0,0],[0,0]])
    for c,o,s,cut,rid,m in res:
        if m is None: continue
        i=0 if cut is None else 1
        a=A[c][i]; a[0]+=m>0; a[1]+=1; a[2]+=m; O[o][i][0]+=m>0; O[o][i][1]+=1
    keep={}
    for c,(d,n) in sorted(A.items()):
        good= n[0]>=d[0] and n[2]>=d[2]
        if good: keep[c]=sel[c]
        print(f"[{'留' if good else '弃'}] {c:32s} 默认 {d[0]}/{d[1]}({d[2]/max(1,d[1]):+6.0f}) 选带{tuple(sel[c])} {n[0]}/{n[1]}({n[2]/max(1,n[1]):+6.0f})")
    print("分对手 默认→选带:",{o:f"{a[0][0]}/{a[0][1]}→{a[1][0]}/{a[1][1]}" for o,a in O.items()})
    T=[sum(A[c][i][0] for c in A) for i in (0,1)]; N=sum(A[c][0][1] for c in A)
    print(f"合计 默认 {T[0]}/{N} → 选带 {T[1]}/{N}; 留存格 {len(keep)}/{len(sel)}")
    json.dump(keep,open(HERE/f"mix_keep_{key}.json","w"))
