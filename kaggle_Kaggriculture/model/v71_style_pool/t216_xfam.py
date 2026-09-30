"""未判别 6 格 × v56 双臂交叉验证(3 seed)。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
T216=json.load(open(HERE/"t216_final.json"))
CELLS={c:T216[c] for c in ["BAKERY|BRUNCH_SPOT","BRUNCH_SPOT|BAKERY","BRUNCH_SPOT|FARMERS_MARKET",
        "FARMERS_MARKET|FARMERS_MARKET","ICE_CREAM_SHOP|ICE_CREAM_SHOP","PIZZA_SHOP|SMOOTHIE_SHOP"]}
def one(job):
    seed,combo,rid2=job
    if rid2>=0: os.environ["KAG_FORCE_ROUTE2"]=str(rid2)
    else: os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r6fr2_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/v56_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return seed,combo,rid2,float(g.reward(0)-g.reward(1))
    except Exception as e: return seed,combo,rid2,None
if __name__=="__main__":
    jobs=[(s,c,r) for c,rid in CELLS.items() for s in IDX[c][2:5] for r in (-1,rid)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    per=collections.defaultdict(dict)
    for s,c,r,m in res:
        if m is not None: per[(c,s)][r]=m
    for c,rid in sorted(CELLS.items()):
        w=b=n=0
        for (c2,s),v in per.items():
            if c2!=c or rid not in v or -1 not in v: continue
            n+=1; w+=v[rid]>0; b+=v[-1]>0
        mark="免门进" if w>=b else "需门/弃"
        print(f"[{mark}] {c:34s} t216带{rid:3d} vs v56 表{w}/{n} 基线{b}/{n}")
