"""晚切点选带(真实棋盘分半):A 半对代表选 {默认, t288/t432 × 13 带},B 半对两个代表验证。
用法: python late_select.py <类别:newgen|cha> <A|B> [procs]"""
import sys, os, json, glob, hashlib, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
SHORT=[0,100,101,103,107,110,112,115,118,120,123,124,126]
ARMS=[(c,r) for c in (288,432) for r in SHORT]
def half(e): return "A" if int(hashlib.md5(("ls"+str(e)).encode()).hexdigest(),16)%2==0 else "B"
if __name__=="__main__":
    cls,stage=sys.argv[1],sys.argv[2]; procs=int(sys.argv[3]) if len(sys.argv)>3 else 7
    grp=("1042.0","main") if cls=="newgen" else ("1042.0","cha")
    repA="me2965_28" if cls=="newgen" else "engineV3"; repsB=["guru28","me2965_28"] if cls=="newgen" else ["engineV3"]
    comp={}
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    seen=set(); B=[]
    for fn in ("boards_recent.json","boards_all.json"):
        for x in json.load(open(fn)):
            if x.get("seed") is None or (x["key"],x["lin"])!=grp or x["eid"] in seen or x["eid"] not in comp: continue
            seen.add(x["eid"]); x["combo"]="|".join((comp[x["eid"]].get("shops") or [])[:2]); x["half"]=half(x["eid"]); B.append(x)
    A=[x for x in B if x["half"]=="A"]; Hh=[x for x in B if x["half"]=="B"]
    print(cls,"棋盘",len(B),"A",len(A),"B",len(Hh),flush=True)
    if stage=="A":
        jobs=[("r32cut",repA,x["seed"],x["seat"],x["eid"],()) for x in A]+[("r32cut",repA,x["seed"],x["seat"],x["eid"],(f"KAG_CUT{c}={r}",)) for x in A for c,r in ARMS]
        tags=[("default",)]*len(A)+[(c,r) for x in A for c,r in ARMS]
        with ProcessPoolExecutor(procs) as ex: res=list(ex.map(be.one,jobs,chunksize=4))
        S=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,0]))
        cm={x["eid"]:x["combo"] for x in A}
        for tag,(e,d) in zip(tags,res):
            if d is None: continue
            a=S[cm[e]][tag]; a[0]+=d>0; a[1]+=d; a[2]+=1
        pick={}; t0=t1=0
        for c in S:
            b=S[c][("default",)]; k,v=max(((k,v) for k,v in S[c].items() if k!=("default",)),key=lambda kv:(kv[1][0],kv[1][1]))
            t0+=b[0]
            if v[0]>b[0]: pick[c]=list(k); t1+=v[0]; print(f"  [改] {c:32s} 默认 {b[0]}/{b[2]} → t{k[0]}带{k[1]} {v[0]}/{v[2]}")
            else: t1+=b[0]
        print(f"A 半:默认 {t0}/{len(A)} → {t1}/{len(A)},改格 {len(pick)}",flush=True)
        json.dump(pick,open(f"late_pick_{cls}.json","w"))
    else:
        pick=json.load(open(f"late_pick_{cls}.json")); T=[x for x in Hh if x["combo"] in pick]
        print("B 半受影响",len(T),flush=True)
        for rep in repsB:
            j0=[("v54r32",rep,x["seed"],x["seat"],x["eid"],()) for x in T]
            j1=[("r32cut",rep,x["seed"],x["seat"],x["eid"],(f"KAG_CUT{pick[x['combo']][0]}={pick[x['combo']][1]}",)) for x in T]
            with ProcessPoolExecutor(procs) as ex: d0=dict(ex.map(be.one,j0)); d1=dict(ex.map(be.one,j1))
            w0=sum(1 for x in T if (d0.get(x["eid"]) or 0)>0); w1=sum(1 for x in T if (d1.get(x["eid"]) or 0)>0)
            print(f"  B 半 vs {rep}: r32 {w0}/{len(T)} → 晚切 {w1}/{len(T)}",flush=True)
