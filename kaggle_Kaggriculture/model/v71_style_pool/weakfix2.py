"""弱项补格·第二轮:4 个难格用全 41 带 + 12 个 1/2 格用短名单,vs rescue7 选值。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]; IDX2=json.load(open(HERE/"combo_index2.json"))["v54"]
FULL=[-1,0,1,3,4,5,6,7,8,9,10,11,12,100,101,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128]
SHORT=[-1,0,100,101,103,107,110,111,112,115,118,120,123,124,126]
HARD=["SMOOTHIE_SHOP|PET_CAFE","FARMERS_MARKET|BRUNCH_SPOT","YARN_STORE|BRUNCH_SPOT","PET_CAFE|ICE_CREAM_SHOP"]
SOFT=["FARMERS_MARKET|PET_CAFE","ICE_CREAM_SHOP|SMOOTHIE_SHOP","BAKERY|PET_CAFE","BRUNCH_SPOT|FARMERS_MARKET",
      "SMOOTHIE_SHOP|FARMERS_MARKET","FARMERS_MARKET|BAKERY","ICE_CREAM_SHOP|BAKERY","ICE_CREAM_SHOP|PET_CAFE",
      "BRUNCH_SPOT|BAKERY","SMOOTHIE_SHOP|SMOOTHIE_SHOP"]
def one(job):
    c,seed,rid=job
    os.environ["KAG_FORCE_ROUTE"]=str(rid); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/rescue7_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return c,seed,rid,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,seed,rid,None
if __name__=="__main__":
    jobs=[]
    for c in HARD+SOFT:
        cands=FULL if c in HARD else SHORT
        seeds=(IDX.get(c,[])[:3]+IDX2.get(c,[])[:2])
        for s in seeds:
            for r in cands: jobs.append((c,s,r))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"weakfix2_sel.json","w"))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,s,r,m in res:
        if m is None: continue
        a=agg[c][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    draft={}
    for c in HARD+SOFT:
        rows=agg[c]
        if not rows: continue
        bw,bn,bm=rows.get(-1,[0,0,0.0])
        cands=[(r,v) for r,v in rows.items() if r!=-1 and v[0]>=max(3,bw+1)]
        if not cands:
            print(f"{c:32s} 基线 {bw}/{bn} -> 无合格候选(需 >=3/5 且优于基线)"); continue
        best=max(cands,key=lambda kv:(kv[1][0],kv[1][2]))
        draft[c]=best[0]
        print(f"{c:32s} 基线 {bw}/{bn}({bm/max(1,bn):+.0f}) -> 带{best[0]:4d} {best[1][0]}/{best[1][1]}({best[1][2]/max(1,best[1][1]):+.0f})")
    json.dump(draft, open(HERE/"weakfix2_draft.json","w"))
    print("入围", len(draft))
