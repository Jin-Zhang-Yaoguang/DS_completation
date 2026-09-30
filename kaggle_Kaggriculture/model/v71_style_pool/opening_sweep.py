"""开局变体镜像扫描:纯底盘(无表)+ 开局变体 vs {rescue7, herdsafe},固定 seed。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
SEEDS=[s for c,ss in sorted(IDX.items()) for s in ss[:1]][:32]
VARS=["o20_15","o12_7","o10_5","o8_3","o7_2","o6_1","o5_0"]
def one(job):
    v,o,seed=job
    os.environ.pop("KAG_FORCE_ROUTE",None); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/op_{v}_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{o}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed); t=0; c72=None
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]
            if t==72: c72=float(obs[0]["farms"][0]["money"])-float(obs[0]["farms"][1]["money"])
            g.step(me(obs[0]),op(obs[1])); t+=1
        return v,o,c72,float(g.reward(0)-g.reward(1))
    except Exception as e: return v,o,None,None
if __name__=="__main__":
    jobs=[(v,o,s) for v in VARS for o in ("rescue7","herdsafe") for s in SEEDS]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump([list(r) for r in res],open(HERE/"opening_sweep.json","w"))
    agg=collections.defaultdict(lambda:[0,0,0.0,0.0,0])
    for v,o,c72,m in res:
        if m is None: continue
        a=agg[(v,o)]; a[0]+= m>0; a[1]+=1; a[2]+=m; a[3]+= (c72 or 0); a[4]+= m==0
    print(f"{'开局(买/卖)':12s} {'vs rescue7':>22s} {'vs herdsafe':>22s}   t72现金差(r7/hs)")
    for v in VARS:
        r=agg[(v,"rescue7")]; h=agg[(v,"herdsafe")]
        print(f"{v:12s} {r[0]:3d}/{r[1]:2d} 平{r[4]:2d} 均{r[2]/max(1,r[1]):+6.0f}   {h[0]:3d}/{h[1]:2d} 平{h[4]:2d} 均{h[2]/max(1,h[1]):+6.0f}   {r[3]/max(1,r[1]):+5.1f}/{h[3]/max(1,h[1]):+5.1f}")
