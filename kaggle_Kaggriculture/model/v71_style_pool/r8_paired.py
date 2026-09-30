"""r8 索引配对验收:重放 A 阶段 128 局(r8 vs rescue7),与 r6 基线逐局对照。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
A=json.load(open(HERE/"t216_a.json"))
def one(job):
    seed,combo=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54r8_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/rescue7_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return seed,combo,float(g.reward(0)-g.reward(1))
    except Exception as e: return seed,combo,None
if __name__=="__main__":
    jobs=[(s,c) for s,c,m in A if m is not None]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    old={(s,c):m for s,c,m in A if m is not None}
    W=sum(1 for s,c,m in res if m and m>0); OW=sum(1 for v in old.values() if v>0)
    flip=[(c,s,round(old[(s,c)]),round(m)) for s,c,m in res if m is not None and (m>0)!=(old[(s,c)]>0)]
    print(f"配对 {len(res)} 局: r8 {W} 胜 | r6 {OW} 胜")
    for c,s,o,n in sorted(flip): print(f"  {'↑' if n>o else '↓'} {c} seed{s} {o:+d}->{n:+d}")
