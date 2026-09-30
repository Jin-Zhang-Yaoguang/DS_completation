"""全量候选草案留出复验:独立 seed 11900-11999。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
K52={"BAKERY|BAKERY":3,"BAKERY|SMOOTHIE_SHOP":111,"BRUNCH_SPOT|BRUNCH_SPOT":110,"PET_CAFE|BAKERY":124,
     "PET_CAFE|YARN_STORE":118,"PIZZA_SHOP|SMOOTHIE_SHOP":120,"PIZZA_SHOP|YARN_STORE":126,
     "SMOOTHIE_SHOP|PIZZA_SHOP":0,"YARN_STORE|SMOOTHIE_SHOP":126}
R7={"BAKERY|BAKERY":112,"BAKERY|SMOOTHIE_SHOP":103,"BRUNCH_SPOT|BRUNCH_SPOT":110,"BRUNCH_SPOT|ICE_CREAM_SHOP":103,
    "FARMERS_MARKET|BRUNCH_SPOT":110,"FARMERS_MARKET|YARN_STORE":0,"ICE_CREAM_SHOP|BRUNCH_SPOT":110,
    "PET_CAFE|BAKERY":124,"PET_CAFE|PIZZA_SHOP":123,"PET_CAFE|YARN_STORE":118,"PIZZA_SHOP|FARMERS_MARKET":9,
    "PIZZA_SHOP|YARN_STORE":126,"SMOOTHIE_SHOP|PIZZA_SHOP":124,"YARN_STORE|BRUNCH_SPOT":126,"YARN_STORE|SMOOTHIE_SHOP":126}
def play(o,seed,rid,stop=False):
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
    op=fidelity.make_agent(f"sub:{HERE}/agents/{o}_main.py")
    k=engine.load_kagsim(); g=k.Game(seed=seed); t=0; combo=None
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1])); t+=1
        if t==146:
            combo="|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
            if stop: return combo,None
    return combo,float(g.reward(0)-g.reward(1))
def scan(job):
    o,s=job
    try: return o,s,play(o,s,-1,stop=True)[0]
    except Exception: return o,s,None
def ev(job):
    o,s,r=job
    try:
        c,m=play(o,s,r); return o,s,r,c,m
    except Exception: return o,s,r,None,None
if __name__=="__main__":
    jobs=[(o,s) for o in ("v52","v53","rescue7") for s in range(11900,12000)]
    with ProcessPoolExecutor(7) as ex: sc=list(ex.map(scan,jobs,chunksize=4))
    hits=[]
    for o,s,c in sc:
        tab=K52 if o in ("v52","v53") else R7
        if c in tab: hits.append((o,s,c,tab[c]))
    print("扫描",len(sc),"命中",len(hits),flush=True)
    jobs=[(o,s,r) for o,s,c,rid in hits for r in (-1,rid)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(ev,jobs,chunksize=2))
    json.dump([list(r) for r in res],open(HERE/"full_cand_verify.json","w"))
    per=collections.defaultdict(dict)
    for o,s,r,c,m in res:
        if m is not None: per[(o,s,c)][r]=m
    byc=collections.defaultdict(lambda:[0,0,0])
    for (o,s,c),v in per.items():
        fam="K52" if o in ("v52","v53") else "R7"
        tab=K52 if fam=="K52" else R7
        rid=tab[c]
        if rid not in v or -1 not in v: continue
        x=byc[(fam,c,rid)]; x[0]+=v[rid]>0; x[1]+=v[-1]>0; x[2]+=1
    for (fam,c,rid),x in sorted(byc.items()):
        mark="进" if x[0]>x[1] else ("平" if x[0]==x[1] else "弃")
        print(f"  [{mark}] {fam:4s} {c:30s} 带{rid:3d} 表{x[0]}/{x[2]} 基线{x[1]}/{x[2]}")
