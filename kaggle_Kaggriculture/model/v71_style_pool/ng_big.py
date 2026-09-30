"""新版人群大种子重选(r36 底盘):54 组合(除 r36 奶类 10 格)× 6 大种子 × {现状, t144×13, 晚切 t288/t432×7, 去 r33 晚切}。"""
import sys, json, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
SHORT=[0,100,101,103,107,110,112,115,118,120,123,124,126]
LATE=[0,100,103,110,112,120,124]
if __name__=="__main__":
    stage=sys.argv[1]
    IDX=json.load(open("combo_big.json"))["v54"]
    ns={}; exec(open("agents/v54r36_main.py").read(), ns)
    milk36={"|".join(k) for k in ns["_R36_MILK"]}; late33={"|".join(k) for k in ns["_R33_NEWGEN_LATE"]}
    cells=[c for c in sorted(IDX) if c not in milk36]
    if stage=="A":
        jobs=[];tags=[]
        for c in cells:
            arms=[("现状",())]+[(f"t144带{r}",(f"KAG_CUT144={r}",)) for r in SHORT]+[(f"t{t}带{r}",(f"KAG_CUT{t}={r}",)) for t in (288,432) for r in LATE]
            if c in late33: arms.append(("去r33晚切",("KAG_NO_R33LATE=1",)))
            for i in range(0,6):
                sd=IDX[c][i]
                for name,env in arms: jobs.append(("r36cut","me2965_28",sd,i%2,f"{c}#{sd}",env)); tags.append((c,name,env))
        print("任务",len(jobs),flush=True)
        with ProcessPoolExecutor(7) as ex: res=list(ex.map(be.one,jobs,chunksize=8))
        S=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,0,None]))
        for (c,name,env),(e,d) in zip(tags,res):
            if d is None: continue
            a=S[c][name]; a[0]+=d>0; a[1]+=d; a[2]+=1; a[3]=env
        pick={}; t0=t1=0
        for c in cells:
            b=S[c]["现状"]; k,v=max(((k,v) for k,v in S[c].items() if k!="现状"),key=lambda kv:(kv[1][0],kv[1][1]))
            t0+=b[0]
            if v[0]>=b[0]+2: pick[c]=[k,list(v[3])]; t1+=v[0]; print(f"  [改] {c:32s} 现状 {b[0]}/{b[2]} → {k} {v[0]}/{v[2]}")
            else: t1+=b[0]
        print(f"A:现状 {t0}/{len(cells)*6} → {t1}/{len(cells)*6},改格 {len(pick)}",flush=True)
        json.dump(pick,open("ngbig_pick.json","w"))
    else:
        pick=json.load(open("ngbig_pick.json"))
        j0=[];j1=[]
        for c,(name,env) in pick.items():
            for i in range(8,16):
                if i>=len(IDX[c]): continue
                sd=IDX[c][i]; j0.append(("r36cut","me2965_28",sd,i%2,f"{c}#{sd}",())); j1.append(("r36cut","me2965_28",sd,i%2,f"{c}#{sd}",tuple(env)))
        with ProcessPoolExecutor(7) as ex: d0=dict(ex.map(be.one,j0,chunksize=4)); d1=dict(ex.map(be.one,j1,chunksize=4))
        print(f"  大种子验证(idx8-15) vs me2965_28: 现状 {sum(1 for v in d0.values() if v and v>0)}/{len(j0)} → 新 {sum(1 for v in d1.values() if v and v>0)}/{len(j1)}",flush=True)
        import glob
        comp={}
        for f in glob.glob("rlive3/*.json"):
            r=json.load(open(f)); comp[str(r["eid"])]=r
        seen=set(); B=[]
        for fn in ("boards_recent.json","boards_all.json","fp_class_rows.json"):
            for x in json.load(open(fn)):
                if x.get("seed") is None or x["eid"] in seen or x["eid"] not in comp or (x.get("key"),x.get("lin"))!=("1042.0","main"): continue
                seen.add(x["eid"]); c="|".join((comp[x["eid"]].get("shops") or [])[:2])
                if c in pick: B.append((x,c))
        for opp in ("me2965_28","harvest29"):
            k0=[("r36cut",opp,x["seed"],x["seat"],x["eid"],()) for x,c in B]; k1=[("r36cut",opp,x["seed"],x["seat"],x["eid"],tuple(pick[c][1])) for x,c in B]
            with ProcessPoolExecutor(7) as ex: e0=dict(ex.map(be.one,k0,chunksize=2)); e1=dict(ex.map(be.one,k1,chunksize=2))
            print(f"  真实棋盘({len(B)} 盘) vs {opp}: 现状 {sum(1 for v in e0.values() if v and v>0)} → 新 {sum(1 for v in e1.values() if v and v>0)}",flush=True)
