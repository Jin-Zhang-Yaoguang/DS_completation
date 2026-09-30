"""新公开对手 bench:09-25 社区新 agent × 64 组合 × 1 seed(combo_index3 独立种子)。
用法: python bench_pub.py <版本>  → bench_pub_<版本>.json"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
P=HERE/"agents"/"pub0925"
OPPS={"harvestledger":P/"haodou092__kaggriculture-harvest-ledger/main.py",
      "hybrid2965":P/"haideptry__the-2965-master-hybrid-engine/main.py",
      "engineV3":P/"guruprasaathas111__kaggriculture-master-engine-v3/main.py",
      "evgen0924":P/"evgendvorkin__kaggriculture/main.py",
      "shepledger":P/"haideptry__the-shepherds-ledger-herd-safe-sovereign/main.py",
      "godsmode":P/"leoprovorov__god-s-mode-hacked-stores/gods_mode_hacked_stores/main.py",
      "idleseller":P/"lynnsakurai__farmer-john-and-the-idle-seller/v57_agent/main.py",
      "pipe18":P/"nathanjacob__kaggriculture-pipe18-six-layers/main.py",
      "v40chal":P/"arsgorynich__kaggriculture-v40-challenger/main.py",
      "v57fo":P/"ahmedberatozer__kaggriculture-v57-funding-order-invariant/v57_agent/main.py",
      "cha22":P/"abhinav0370__cha22-agent/main.py",
      "demandpres":P/"tetsutani__demand-preserving-turn-sale-timing/main.py",
      "poprobust":P/"nihilisticneuralnet__kaggriculture-population-robust-economy/main.py",
      "guruV4":P.parent/"pub0926"/"guruprasaathas111__kaggriculture-top-2-master-engine-v4/main.py",
      "harvest2":P.parent/"pub0926"/"haodou092__kaggriculture-harvest-ledger/main.py",
      "demand2":P.parent/"pub0926"/"tetsutani__demand-preserving-turn-sale-timing/main.py",
      "multiroute2":P.parent/"pub0926"/"flexonafft__kaggriculture-multi-route-farming-agent/main.py",
      "shep28":P.parent/"pub0928"/"haideptry__the-shepherds-ledger-herd-safe-sovereign/main.py",
      "harvest28":P.parent/"pub0928"/"haodou092__kaggriculture-harvest-ledger/main.py",
      "guru28":P.parent/"pub0928"/"guruprasaathas111__kaggriculture-top-2-master-engine-v4/main.py",
      "hybrid28":P.parent/"pub0928"/"haideptry__the-2965-master-hybrid-engine/main.py",
      "demand28":P.parent/"pub0928"/"tetsutani__demand-preserving-turn-sale-timing/main.py",
      "me2965_28":P.parent/"pub0928"/"leoprovorov__2965-master-engine/main.py",
      "idle28":P.parent/"pub0928"/"lynnsakurai__farmer-john-and-the-idle-seller/main.py"}
IDX=json.load(open(HERE/"combo_index3.json"))["v54"]
def one(job):
    ver,o,seed,combo=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    sys.path.insert(0,str(OPPS[o].parent))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
        op=fidelity.make_agent(f"sub:{OPPS[o]}")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return o,seed,combo,float(g.reward(0)-g.reward(1))
    except Exception as e: return o,seed,combo,None
if __name__=="__main__":
    ver=sys.argv[1]; opps=sys.argv[2].split(",") if len(sys.argv)>2 else list(OPPS)
    jobs=[(ver,o,s[0],c) for o in opps for c,s in sorted(IDX.items())]
    print(f"{ver}: {len(jobs)} 局",flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    json.dump([list(r) for r in res],open(HERE/f"bench_pub_{ver}{os.environ.get('BENCH_TAG','')}.json","w"))
    byo=collections.defaultdict(lambda:[0,0,0.0,0])
    for o,s,c,m in res:
        if m is None: byo[o][3]+=1; continue
        a=byo[o]; a[0]+= m>0; a[1]+=1; a[2]+=m
    for o,a in byo.items(): print(f"  vs {o:14s} {a[0]:3d}/{a[1]:3d} ({a[0]/max(1,a[1]):5.1%}) 均差 {a[2]/max(1,a[1]):+7.0f} 失败{a[3]}")
