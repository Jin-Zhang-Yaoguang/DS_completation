"""拼接留出复验:7 格 × 新 seed × {rescue7, herdsafe, v56(跨族安全)} × {不切, 拼接}。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IR7b=json.load(open(HERE/"combo_index2.json"))["v54"]
IHS=json.load(open(HERE/"combo_index_hs.json"))["herdsafe"]
CAND={"FARMERS_MARKET|BRUNCH_SPOT":(360,101),"YARN_STORE|BRUNCH_SPOT":(432,101),"PIZZA_SHOP|PET_CAFE":(360,112),
      "YARN_STORE|BAKERY":(360,120),"FARMERS_MARKET|YARN_STORE":(432,0),"FARMERS_MARKET|PIZZA_SHOP":(360,100),
      "ICE_CREAM_SHOP|SMOOTHIE_SHOP":(360,112)}
def one(job):
    c,opp,seed,cut,rid=job
    for k in list(os.environ):
        if k.startswith("KAG_CUT") or k.startswith("KAG_FORCE"): os.environ.pop(k,None)
    if cut: os.environ[f"KAG_CUT{cut}"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r19cut_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return c,opp,cut,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,opp,cut,None
if __name__=="__main__":
    jobs=[]
    for c,(cut,rid) in CAND.items():
        for opp,seeds in (("rescue7",IR7b.get(c,[])[:6]),("herdsafe",IHS.get(c,[])[3:9]),("v56",IR7b.get(c,[])[6:10])):
            for s in seeds:
                jobs.append((c,opp,s,None,-1)); jobs.append((c,opp,s,cut,rid))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump([list(r) for r in res],open(HERE/"splice_holdout.json","w"))
    per=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,opp,cut,m in res:
        if m is None: continue
        a=per[(c,opp)]["s" if cut else "b"]; a[0]+= m>0; a[1]+=1; a[2]+=m
    final={}
    for c,(cut,rid) in sorted(CAND.items()):
        cols=[]; tw=tb=0; tm=0.0; safe=True
        for opp in ("rescue7","herdsafe","v56"):
            b=per[(c,opp)]["b"]; s=per[(c,opp)]["s"]
            cols.append(f"{opp}:{s[0]}/{s[1]}(基{b[0]}) Δ均{(s[2]-b[2])/max(1,s[1]):+6.0f}")
            tw+=s[0]; tb+=b[0]; tm+=(s[2]-b[2])
            if s[0]<b[0]: safe=False
        ok = tw>tb or (tw==tb and tm>0 and safe)
        if ok and safe: final[c]=[cut,rid]
        tag = "进" if (ok and safe) else ("族劣" if not safe else "弃")
        print(f"[{tag}] {c:30s} t{cut}->{rid:3d}  总胜 {tw} vs 基 {tb} | " + " | ".join(cols))
    json.dump(final, open(HERE/"splice_final.json","w"))
    print("终进", len(final))
