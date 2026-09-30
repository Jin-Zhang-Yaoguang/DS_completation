"""方向0 羊缺口诊断:同种子 我方(r38c) vs 代表,逐步买畜时点/数量、场上畜群、牧羊模块计数(_V233_REPORT)。
双方都在本进程内 exec 以读取模块内部计数。"""
import sys, json, collections, os
from concurrent.futures import ProcessPoolExecutor
M="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model"
def load(path):
    ns={"__name__":"agent_mod"}; d=os.path.dirname(path)
    if d not in sys.path: sys.path.insert(0,d)
    exec(compile(open(path).read(),path,"exec"),ns)
    fn=[v for k,v in ns.items() if callable(v) and getattr(v,"__module__",None) in (None,"agent_mod") and hasattr(v,"__code__")][-1]
    return ns,fn
def herd(f):
    c=collections.Counter()
    for row in f["tiles"]:
        for t in row:
            if isinstance(t,dict) and t.get("animal"): c[t["animal"]]+=1
    return c
def one(job):
    me_path,op_path,seed,seat=job
    sys.path.insert(0,M+"/v4_demand_race/harness"); import engine
    try:
        nsA,A=load(me_path); nsB,B=load(op_path)
        for ns in (nsA,nsB):
            if "_V233_REPORT" in ns:
                for k in ns["_V233_REPORT"]: ns["_V233_REPORT"][k]=0
        k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat; t=0
        buys=[[],[]]; H={}
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=A(obs[seat]); a[o]=B(obs[o])
            for i,p in enumerate((seat,o)):
                for x in ((a[p] or {}).get("market") or []):
                    if x and x[0]=="BUY_ANIMAL":
                        try: n=int(x[2]) if len(x)>2 else 1
                        except Exception: n=1
                        buys[i].append((t,x[1],n,obs[p]["farms"][p]["money"]))
            if t in (144,200,264,300,432,600): H[t]=(dict(herd(obs[0]["farms"][seat])),dict(herd(obs[0]["farms"][o])))
            g.step(a[0],a[1]); t+=1
        shops=tuple((g.observe(0)["town"]["unlocked_shops"] or [])[:2])
        rep=[dict(nsA.get("_V233_REPORT",{})),dict(nsB.get("_V233_REPORT",{}))]
        return job,dict(d=float(g.reward(seat)-g.reward(o)),buys=buys,H=H,rep=rep,shops=shops)
    except Exception as ex: return job,{"err":str(ex)[:120]}
if __name__=="__main__":
    HERE=os.path.dirname(os.path.abspath(__file__))
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    me=f"{HERE}/agents/v54r38c_main.py"; ops=sys.argv[1].split(",")
    jobs=[(me,f"{HERE}/agents/{o}_main.py",IDX[c][2],st) for o in ops for c in cells for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: R=list(ex.map(one,jobs,chunksize=2))
    out=[]
    for j,v in R:
        if "err" in v: continue
        v["opp"]=os.path.basename(j[1]).replace("_main.py",""); v["seed"]=j[2]; v["seat"]=j[3]; out.append(v)
    json.dump(out,open("sheep_diag.json","w"))
    print("有效局",len(out),"错误",sum(1 for _,v in R if "err" in v), [v["err"] for _,v in R if "err" in v][:2])
    for o in ops:
        S=[v for v in out if v["opp"]==o]
        tb=lambda i,an: sum(sum(n for t,a,n,m in v["buys"][i] if a==an) for v in S)/max(1,len(S))
        print(f"\n== vs {o} n={len(S)}  平均买畜(我/对): 羊 {tb(0,'SHEEP'):.1f}/{tb(1,'SHEEP'):.1f}  牛 {tb(0,'COW'):.1f}/{tb(1,'COW'):.1f}  鹅 {tb(0,'GOOSE'):.1f}/{tb(1,'GOOSE'):.1f}")
        for t in ("144","264","432"):
            hs=[v["H"].get(t) or v["H"].get(int(t)) for v in S]; hs=[h for h in hs if h]
            av=lambda i,a: sum(h[i].get(a,0) for h in hs)/max(1,len(hs))
            print(f"   t{t} 场上 我 羊{av(0,'SHEEP'):.1f} 牛{av(0,'COW'):.1f} 鹅{av(0,'GOOSE'):.1f} | 对 羊{av(1,'SHEEP'):.1f} 牛{av(1,'COW'):.1f} 鹅{av(1,'GOOSE'):.1f}")
        keys=sorted({k for v in S for k in v["rep"][0]}|{k for v in S for k in v["rep"][1]})
        print("   牧羊模块计数(我/对,均值): "+"  ".join(f"{k.replace('sheep_','')}:{sum(v['rep'][0].get(k,0) for v in S)/len(S):.1f}/{sum(v['rep'][1].get(k,0) for v in S)/len(S):.1f}" for k in keys))
