"""按人群的开环对手池评估:python ana/cls_pool.py AGENTS [new]  (new=只用选分支之后新增的线上对局,样本外)"""
import json,sys,os,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent; os.chdir(HERE); sys.path.insert(0,str(HERE))
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
import sel_cls
def job(j):
    os.environ.pop("KAG_V55_OVR",None); r=sim(j)[1]; return j,(r or {}).get("d")
if __name__=="__main__":
    AG=sys.argv[1].split(","); new=len(sys.argv)>2 and sys.argv[2]=="new"
    NEW=set(json.load(open("ana/new_online_eids.json")))
    U=[]
    for k in "PAL":
        for c,L in sel_cls.boards(k).items():
            for src,eid,s in L:
                isnew=(src=="rlive3" and eid in NEW)
                if new!=isnew: continue
                U.append((k,src,eid,s))
    # 其他人群(O)的新增线上局
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(job,[(a,src,eid,s,()) for a in AG for k,src,eid,s in U],chunksize=8))
    T=collections.defaultdict(lambda:collections.defaultdict(list))
    for k,src,eid,s in U:
        for a in AG:
            d=R.get((a,src,eid,s,()))
            if d is not None: T[k][a].append(d); T["合计"][a].append(d)
    for k in ("P","A","L","合计"):
        if k in T: print(f"  {k:3s} n={len(T[k][AG[0]]):5d} "+"  ".join(f"{a}: {sum(x>0 for x in T[k][a])/len(T[k][a]):5.1%}({sum(T[k][a])/len(T[k][a]):6.0f})" for a in AG))
