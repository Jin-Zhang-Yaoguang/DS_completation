"""键映射测试:r26km × KAG_KEYMAP 变体 × 开局变体代理 × 64 组合 × 2 种子。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/os.environ.get("KM_INDEX","combo_index3.json")))["v54"]; SIS=[int(x) for x in os.environ.get("KM_SEEDS","0,1").split(",")]
def one(job):
    km,opp,c,seed=job
    os.environ["KAG_KEYMAP"]=km
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{os.environ.get('KM_AGENT','r26km')}_main.py"); op=fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return km,opp,c,seed,float(g.reward(0)-g.reward(1))
    except Exception as e: return km,opp,c,seed,None
if __name__=="__main__":
    plans=json.loads(sys.argv[1])  # {opp:[km,...]}
    jobs=[(km,o,c,s[min(i,len(s)-1)]) for o,kms in plans.items() for km in kms for c,s in sorted(IDX.items()) for i in SIS]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump(res,open(HERE/f"km_test_{sys.argv[2]}.json","w"))
    A=collections.defaultdict(lambda:[0,0,0.0])
    for km,o,c,s,m in res:
        if m is None: continue
        a=A[(o,km)]; a[0]+=m>0; a[1]+=1; a[2]+=m
    for (o,km),a in sorted(A.items()): print(f"  {o:10s} 映射[{km or '无'}] {a[0]}/{a[1]} 均差{a[2]/a[1]:+.0f}")
