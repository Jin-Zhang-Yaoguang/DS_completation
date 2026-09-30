"""t216 工程·B:输局 seed × 16 条 t216 候选,找每格一致翻负带。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
CAND=[0,3,9,100,101,103,107,110,111,112,115,118,120,123,124,126]
A=json.load(open(HERE/"t216_a.json"))
losses=[(s,c) for s,c,m in A if m is not None and m<=0]
def one(job):
    seed,combo,rid2=job
    os.environ["KAG_FORCE_ROUTE2"]=str(rid2)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r6fr2_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/rescue7_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return seed,combo,rid2,float(g.reward(0)-g.reward(1))
    except Exception as e: return seed,combo,rid2,None
if __name__=="__main__":
    jobs=[(s,c,r) for s,c in losses for r in CAND]
    print("输局",len(losses),"任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump([list(r) for r in res],open(HERE/"t216_b.json","w"))
    per=collections.defaultdict(dict)
    for s,c,r,m in res:
        if m is not None: per[(c,s)][r]=m
    # 每格:两个输局 seed 都翻的带(单输局格=该局翻)
    draft={}
    byc=collections.defaultdict(list)
    for (c,s),v in per.items(): byc[c].append(v)
    for c,vs in sorted(byc.items()):
        common=[r for r in CAND if all(v.get(r,0)>0 for v in vs)]
        if common: draft[c]=common[0]
        print(f"{c:34s} 输局{len(vs)} 一致翻负带 {common[:6]}")
    json.dump(draft, open(HERE/"t216_draft.json","w"))
    print("有解格", len(draft), "/", len(byc))
