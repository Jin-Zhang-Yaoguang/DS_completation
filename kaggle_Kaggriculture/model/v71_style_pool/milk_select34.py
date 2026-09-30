"""奶类世界多种子重选(r34 底盘):39 奶类组合 × 8 种子(combo_index6 idx10-17) × {r34 当前, t144 候选带} vs me2965_28。"""
import sys, json, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
MILK={"PIZZA_SHOP","ICE_CREAM_SHOP","SMOOTHIE_SHOP"}
CANDS=[124,107,103,105,106,110,112,120,125,0,115]
if __name__=="__main__":
    stage=sys.argv[1]
    IDX=json.load(open("combo_index6.json"))["v54"]
    cells=[c for c in sorted(IDX) if MILK & set(c.split("|"))]
    if stage=="A":
        jobs=[];tags=[]
        for c in cells:
            for i in range(10,18):
                sd=IDX[c][i]
                jobs.append(("v54r34","me2965_28",sd,0,f"{c}#{sd}",())); tags.append((c,"r34"))
                for r in CANDS: jobs.append(("r34cut","me2965_28",sd,0,f"{c}#{sd}",(f"KAG_CUT144={r}",))); tags.append((c,r))
        print("任务",len(jobs),flush=True)
        with ProcessPoolExecutor(7) as ex: res=list(ex.map(be.one,jobs,chunksize=6))
        S=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,0]))
        for (c,arm),(e,d) in zip(tags,res):
            if d is None: continue
            a=S[c][arm]; a[0]+=d>0; a[1]+=d; a[2]+=1
        pick={}; t0=t1=0
        for c in cells:
            b=S[c]["r34"]; k,v=max(((k,v) for k,v in S[c].items() if k!="r34"),key=lambda kv:(kv[1][0],kv[1][1]))
            t0+=b[0]
            if v[0]>=b[0]+2: pick[c]=[144,k]; t1+=v[0]; print(f"  [改] {c:32s} r34 {b[0]}/{b[2]} → 带{k} {v[0]}/{v[2]}")
            else: t1+=b[0]
        print(f"A:r34 {t0}/{len(cells)*8} → {t1}/{len(cells)*8},改格 {len(pick)}",flush=True)
        json.dump(pick,open("milk34_pick.json","w"))
    else:
        pick=json.load(open("milk34_pick.json"))
        for opp,idxs in (("guru28",range(18,22)),("harvest29",range(18,22)),("me2965_28",range(18,22))):
            j0=[];j1=[]
            for c,(cut,r) in pick.items():
                for i in idxs:
                    if i>=len(IDX[c]): continue
                    sd=IDX[c][i]; j0.append(("v54r34",opp,sd,0,f"{c}#{sd}",())); j1.append(("r34cut",opp,sd,0,f"{c}#{sd}",(f"KAG_CUT144={r}",)))
            with ProcessPoolExecutor(7) as ex: d0=dict(ex.map(be.one,j0,chunksize=4)); d1=dict(ex.map(be.one,j1,chunksize=4))
            print(f"  验证 vs {opp}: r34 {sum(1 for v in d0.values() if v and v>0)}/{len(j0)} → 新带 {sum(1 for v in d1.values() if v and v>0)}/{len(j1)}",flush=True)
