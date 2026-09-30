"""人群混合面板选带:每格 × {r22默认, t144 全 13 带, 粗筛该格最优晚切点} × 面板全部同键方案 × 1 seed。
用法: python mix_select.py <键 1039|1042> <seed序号>  → mix_select_<键>_s<序号>.json"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
from pub_splice import one, OPP, SHORT, IDX
PANEL={"1039":["rescue7","harvestledger","hybrid2965","hai2965","guru_v4","idleseller","pipe18","v40chal","v57fo"],
       "1042":["herdsafe","engineV3","shepledger","cha22","demandpres"]}
def coarse_best(key):
    res=json.load(open(HERE/f"pub_splice_k{key}.json")); agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0]))
    for c,o,s,cut,rid,m in res:
        if m is None: continue
        a=agg[c][(cut,rid)]; a[0]+=m>0; a[1]+=m
    return {c:max(r.items(),key=lambda kv:(kv[1][0],kv[1][1]))[0] for c,r in agg.items()}
if __name__=="__main__":
    key=sys.argv[1]; si=int(sys.argv[2]); cb=coarse_best(key)
    jobs=[]
    for c,s in sorted(IDX.items()):
        arms={(None,-1)}|{(144,r) for r in SHORT}|{tuple(cb[c])}
        for o in PANEL[key]:
            for cut,rid in arms: jobs.append((c,o,s[min(si,len(s)-1)],cut,rid))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/f"mix_select_{key}_s{si}.json","w"))
    print("完成")
