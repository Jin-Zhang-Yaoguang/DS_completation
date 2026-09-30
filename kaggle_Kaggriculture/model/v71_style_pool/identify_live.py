"""线上 1039 对手身份鉴定:在同 seed 上让我方原版(r20/r22)对各候选方案仿真,比较对手动作与线上一致的步数。
一致到终局 = 就是该方案(或行为等价 fork)。"""
import sys, json, glob, os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
G={"1039.0":["rescue7","harvestledger","harvest2","guruV4","hybrid2965","hai2965","guru_v4","idleseller","pipe18","v40chal","v57fo"],
   "1042.0":["herdsafe","engineV3","shepledger","cha22","demandpres"],
   "1049.0":["metav4","godsmode","poprobust"]}
H=json.load(open(HERE/"rkey_head.json"))
def norm(a): return json.dumps({k:a.get(k) for k in ("farmer","hands","market")},sort_keys=True)
def one(job):
    fn,cand=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[cand]).parent))
    import fidelity, engine
    r=json.load(open(fn)); seat=r["seat"]; o=1-seat; ver=r["meta"]
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54{ver}_main.py"); op=fidelity.make_agent(f"sub:{OPP[cand]}")
        k=engine.load_kagsim(); g=k.Game(seed=r["seed"]); t=0; first_me=first_op=None
        while not engine._val(g.done) and t<719:
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o])
            live=r["acts"][t+1]
            if first_me is None and norm(a[seat])!=norm(live[seat]): first_me=t
            if first_op is None and norm(a[o])!=norm(live[o]): first_op=t
            if first_op is not None: break
            g.step(a[0],a[1]); t+=1
        return fn,cand,first_me,first_op
    except Exception as e: return fn,cand,"ERR",str(e)[:80]
if __name__=="__main__":
    fs=sorted(glob.glob(str(HERE/"rlive3/*.json")))
    done=json.load(open(HERE/"identify_live.json")) if (HERE/"identify_live.json").exists() else {}
    jobs=[]
    for f in fs:
        e=Path(f).stem; rk=H.get(e,{}).get("rkey")
        if not rk or json.load(open(f))["meta"] not in tuple(os.environ.get("ID_VERS","r20,r22").split(",")): continue
        for c in G.get(str(rk[0]),[]):
            if c not in done.get(e,{}): jobs.append((f,c))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(int(sys.argv[2]) if len(sys.argv)>2 else 3) as ex: res=list(ex.map(one,jobs))
    out=done
    for fn,c,fm,fo in res: out.setdefault(Path(fn).stem,{})[c]=(fm,fo)
    json.dump(out,open(HERE/"identify_live.json","w"))
    print("完成",len(out))
