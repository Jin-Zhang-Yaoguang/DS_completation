"""本地对打平局原因:逐步比较两农场杂草/地块/动作/现金。"""
import sys, json, os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
def weeds(tiles): return {(x,y) for y,row in enumerate(tiles) for x,c in enumerate(row) if isinstance(c,dict) and c.get("kind")=="WEED"}
def one(job):
    a0,a1,seed,tag=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    A=[fidelity.make_agent(f"sub:{HERE}/agents/{a0}_main.py"),fidelity.make_agent(f"sub:{HERE}/agents/{a1}_main.py")]
    k=engine.load_kagsim(); g=k.Game(seed=seed); t=0
    ft=fa=fm=fw=None; wcount=[set(),set()]
    while not engine._val(g.done):
        o=[g.observe(0),g.observe(1)]; f=o[0]["farms"]
        w=[weeds(f[0]["tiles"]),weeds(f[1]["tiles"])]
        for p in (0,1): wcount[p]|={(x,y,t) for x,y in w[p]} if False else set()
        if fw is None and w[0]!=w[1]: fw=(t,sorted(w[0]-w[1])[:2],sorted(w[1]-w[0])[:2])
        if ft is None and f[0]["tiles"]!=f[1]["tiles"]: ft=t
        if fm is None and f[0]["money"]!=f[1]["money"]: fm=t
        a=[A[0](o[0]),A[1](o[1])]
        if fa is None and json.dumps(a[0],sort_keys=True)!=json.dumps(a[1],sort_keys=True): fa=t
        g.step(a[0],a[1]); t+=1
    return tag,dict(r=(g.reward(0),g.reward(1)),weed_diff=fw,tile_diff=ft,act_diff=fa,money_diff=fm)
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    jobs=[]
    for c in cells[:24]:
        sd=IDX[c][0]
        jobs.append(("v54r38c","v54r34",sd,f"{c}|r38c先"))
        jobs.append(("v54r38c","v54r38c",sd,f"{c}|自对弈"))
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(one,jobs,chunksize=1))
    import collections
    cnt=collections.Counter()
    for tag,x in R.items():
        draw=x["r"][0]==x["r"][1]; kind=tag.split("|")[1]
        cnt[(kind,"平" if draw else "非平","杂草不同" if x["weed_diff"] else "杂草从未不同")]+=1
    for k,v in sorted(cnt.items()): print(k,v)
    print("\n样例(前 10 个平局):")
    for tag,x in [(t,x) for t,x in R.items() if x["r"][0]==x["r"][1]][:10]:
        print(f"  {tag:42s} 奖励 {x['r']} 杂草首次不同 {x['weed_diff']} 地块 t{x['tile_diff']} 动作 t{x['act_diff']} 现金 t{x['money_diff']}")
    print("\n样例(非平局):")
    for tag,x in [(t,x) for t,x in R.items() if x["r"][0]!=x["r"][1]][:6]:
        print(f"  {tag:42s} 奖励 {x['r']} 杂草首次不同 {x['weed_diff']} 地块 t{x['tile_diff']} 动作 t{x['act_diff']} 现金 t{x['money_diff']}")
