"""纱线世界(新版人群)统一改带:A=大种子 idx0-5 选臂(vs me2965_28);B=独立大种子 idx8-15 双代表 + 真实纱线棋盘三代表。"""
import sys, json, collections, os
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
W=int(os.environ.get("KAG_WORKERS","8"))
IDX=json.load(open("combo_big.json"))["v54"]; Y=[c for c in sorted(IDX) if "YARN_STORE" in c.split("|")]
ARMS=[("现状",())]+[(f"t144带{r}",("KAG_CUTYARN=1",f"KAG_CUT144={r}")) for r in (1,3,9,12,126,114,115)]+[("t216带9",("KAG_CUTYARN=1","KAG_CUT216=9"))]
def ev(jobs):
    with ProcessPoolExecutor(W) as ex: return list(ex.map(be.one,jobs,chunksize=2))
if __name__=="__main__":
    st=sys.argv[1]
    if st=="A":
        jobs=[];tags=[]
        for name,env in ARMS:
            for c in Y:
                for i in range(6):
                    sd=IDX[c][i]; jobs.append(("r38cut","me2965_28",sd,i%2,f"{c}#{sd}",env)); tags.append((name,c))
        res=ev(jobs); S=collections.defaultdict(lambda:[0,0,0.0]); C=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0]))
        for (name,c),(e,d) in zip(tags,res):
            if d is None: continue
            S[name][0]+=d>0; S[name][1]+=1; S[name][2]+=d; C[c][name][0]+=d>0; C[c][name][1]+=1
        for name,_ in ARMS: a=S[name]; print(f"  {name:10s} {a[0]}/{a[1]}  均差 {a[2]/max(1,a[1]):7.0f}",flush=True)
        json.dump({k:dict(v) for k,v in C.items()},open("yarn_A_cells.json","w"),ensure_ascii=False)
    else:
        name=sys.argv[2]; env=dict(ARMS)[name]
        for opp in ("me2965_28","guru28"):
            j0=[];j1=[]
            for c in Y:
                for i in range(8,16):
                    if i<len(IDX[c]): sd=IDX[c][i]; j0.append(("r38cut",opp,sd,i%2,f"{c}#{sd}",())); j1.append(("r38cut",opp,sd,i%2,f"{c}#{sd}",env))
            r0=ev(j0); r1=ev(j1)
            print(f"  大种子验证 vs {opp}: 现状 {sum(1 for e,d in r0 if d and d>0)}/{len(j0)} → {name} {sum(1 for e,d in r1 if d and d>0)}/{len(j1)}",flush=True)
        B=[x for x in json.load(open("axis_rows.json")) if x["cls"]=="新版人群" and "YARN_STORE" in x["shops"]]
        for opp in ("me2965_28","guru28","harvest29"):
            k0=[("r38cut",opp,x["seed"],x["seat"],x["eid"],()) for x in B]; k1=[("r38cut",opp,x["seed"],x["seat"],x["eid"],env) for x in B]
            r0=dict(ev(k0)); r1=dict(ev(k1))
            print(f"  真实纱线棋盘({len(B)}) vs {opp}: 现状 {sum(1 for d in r0.values() if d and d>0)} → {sum(1 for d in r1.values() if d and d>0)}",flush=True)
