"""新版人群最优应对搜索:全部 41 条带 t144 强制,真实棋盘分半(A 选 vs me2965_28,B 验 vs guru28+me2965_28)。"""
import sys, json, glob, hashlib, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
def half(e): return "A" if int(hashlib.md5(("cs"+str(e)).encode()).hexdigest(),16)%2==0 else "B"
if __name__=="__main__":
    ns={}; exec(open("agents/v54r33_main.py").read(), ns); ROUTES=sorted(ns["_IMPL"].chassis.routes)
    comp={}
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    seen=set(); B=[]
    for fn in ("boards_recent.json","boards_all.json"):
        for x in json.load(open(fn)):
            if x.get("seed") is None or (x["key"],x["lin"])!=("1042.0","main") or x["eid"] in seen or x["eid"] not in comp: continue
            seen.add(x["eid"]); x["combo"]="|".join((comp[x["eid"]].get("shops") or [])[:2]); x["half"]=half(x["eid"]); B.append(x)
    A=[x for x in B if x["half"]=="A"]; H=[x for x in B if x["half"]=="B"]
    stage=sys.argv[1]
    if stage=="A":
        jobs=[("v54r34","me2965_28",x["seed"],x["seat"],x["eid"],())for x in A]; tags=[("r33",)]*len(A)
        for r in ROUTES:
            jobs+=[("r34cut","me2965_28",x["seed"],x["seat"],x["eid"],(f"KAG_CUT144={r}",)) for x in A]; tags+=[(r,)]*len(A)
        print("A 半",len(A),"盘 × ",len(ROUTES)+1,"臂 =",len(jobs),flush=True)
        with ProcessPoolExecutor(7) as ex: res=list(ex.map(be.one,jobs,chunksize=4))
        cm={x["eid"]:x["combo"] for x in A}
        S=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,0]))
        for tag,(e,d) in zip(tags,res):
            if d is None: continue
            a=S[cm[e]][tag]; a[0]+=d>0; a[1]+=d; a[2]+=1
        json.dump({c:{str(k[0]):v for k,v in d.items()} for c,d in S.items()},open("br_A.json","w"))
        pick={}; t0=t1=0; best_route_use=collections.Counter()
        for c in S:
            b=S[c][("r33",)]; k,v=max(((k,v) for k,v in S[c].items() if k!=("r33",)),key=lambda kv:(kv[1][0],kv[1][1]))
            t0+=b[0]; best_route_use[k[0]]+=1
            if v[0]>b[0]: pick[c]=[144,k[0]]; t1+=v[0]; print(f"  [改] {c:32s} r33 {b[0]}/{b[2]} → 带{k[0]} {v[0]}/{v[2]}")
            else: t1+=b[0]
        tot=collections.Counter()
        for c in S:
            for k,v in S[c].items(): tot[k[0]]+=v[0]
        print("各带在 A 半的总胜局(前10):",tot.most_common(10))
        print(f"A 半:r33 {t0}/{len(A)} → 最优应对 {t1}/{len(A)},改格 {len(pick)}",flush=True)
        json.dump(pick,open("br_pick.json","w"))
    else:
        pick=json.load(open("br_pick.json")); T=[x for x in H if x["combo"] in pick]
        print("B 半受影响",len(T),flush=True)
        for rep in ("guru28","me2965_28"):
            with ProcessPoolExecutor(7) as ex:
                d0=dict(ex.map(be.one,[("v54r34",rep,x["seed"],x["seat"],x["eid"],()) for x in T]))
                d1=dict(ex.map(be.one,[("r34cut",rep,x["seed"],x["seat"],x["eid"],(f"KAG_CUT144={pick[x['combo']][1]}",)) for x in T]))
            print(f"  B 半 vs {rep}: r33 {sum(1 for x in T if (d0.get(x['eid']) or 0)>0)}/{len(T)} → 最优应对 {sum(1 for x in T if (d1.get(x['eid']) or 0)>0)}/{len(T)}",flush=True)
