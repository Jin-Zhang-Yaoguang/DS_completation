"""V233 牧羊加码在不同开关下的触发率(vs me2965,64 组合 × idx20 × 双席位)。"""
import sys, os, json, collections
from concurrent.futures import ProcessPoolExecutor
M="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model"
def one(job):
    env,seed,seat=job
    for k in ("KAG_V233_DAYS","KAG_V233_WOOL","KAG_V233_YARN"): os.environ.pop(k,None)
    for kv in env: k,v=kv.split("=",1); os.environ[k]=v
    sys.path.insert(0,M+"/v4_demand_race/harness"); import engine
    try:
        ns={"__name__":"m"}; exec(open("agents/r38s_main.py").read(),ns); A=ns["_lead_final"]
        B={"__name__":"m"}; exec(open("agents/me2965_28_main.py").read(),B); op=B["agent"]
        k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=A(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        rep=ns["_V233_REPORT"]; sh=g.observe(0)["town"]["unlocked_shops"]
        return job,dict(commit=rep["sheep_committed"],req=rep["sheep_commit_requests"],d=g.reward(seat)-g.reward(o),yarn=sh.count("YARN_STORE"))
    except Exception as ex: return job,None
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    ARMS=[(),("KAG_V233_DAYS=11:12:15:18",),("KAG_V233_WOOL=180",),("KAG_V233_DAYS=11:12:15:18","KAG_V233_WOOL=180")]
    jobs=[(env,IDX[c][20],st) for env in ARMS for c in cells for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: R=list(ex.map(one,jobs,chunksize=2))
    for env in ARMS:
        V=[v for j,v in R if j[0]==env and v]
        y2=[v for v in V if v["yarn"]>=2]
        print(f"{' '.join(env) or '默认'}: 局 {len(V)} 触发加码 {sum(v['commit']>0 for v in V)} (其中终局纱线店≥2 的 {len(y2)} 局里触发 {sum(v['commit']>0 for v in y2)})  胜 {sum(v['d']>0 for v in V)}")
