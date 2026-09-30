"""⑧ t216 试点:找 w48 vs v56 输局,试 t216 二次切带翻负。"""
import sys, os, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
CAND=[0,1,3,5,7,9,100,101,103,107,110,112,115,118,120,123,126,128]
def play(seed,rid2):
    if rid2>=0: os.environ["KAG_FORCE_ROUTE2"]=str(rid2)
    else: os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:{HERE}/agents/w48fr2_main.py")
    op=fidelity.make_agent(f"sub:{HERE}/agents/v56_main.py")
    k=engine.load_kagsim(); g=k.Game(seed=seed)
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
    return float(g.reward(0)-g.reward(1))
def base(s):
    try: return s, play(s,-1)
    except Exception: return s, None
def ev(job):
    s,r=job
    try: return s,r,play(s,r)
    except Exception: return s,r,None
if __name__=="__main__":
    with ProcessPoolExecutor(7) as ex: b=list(ex.map(base,range(10800,10832),chunksize=2))
    losers=[s for s,m in b if m is not None and m<=0]
    print(f"基线 {sum(1 for _,m in b if m and m>0)}/{len(b)} 胜;输局 {len(losers)}",flush=True)
    jobs=[(s,r) for s in losers for r in CAND]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(ev,jobs,chunksize=3))
    per=collections.defaultdict(dict)
    for s,r,m in res:
        if m is not None: per[s][r]=m
    flips=collections.Counter()
    for s,v in per.items():
        wins=[r for r,m in v.items() if m>0]
        if wins: flips.update(wins)
        print(f"seed{s}: 可翻带 {sorted(wins)[:8]}{'...' if len(wins)>8 else ''} ({len(wins)}/{len(v)})")
    print("翻负最稳带:",flips.most_common(6))
