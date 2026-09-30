"""herdsafe 补格:留出复验(herdsafe 新 seed) + 跨键安全(rescue7 索引)。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IHS=json.load(open(HERE/"combo_index_hs.json"))["herdsafe"]
IR7=json.load(open(HERE/"combo_index.json"))["v54"]
IR7b=json.load(open(HERE/"combo_index2.json"))["v54"]
NEW=json.load(open(HERE/"hsfix_draft.json"))
def one(job):
    c,seed,rid,opp=job
    os.environ["KAG_FORCE_ROUTE"]=str(rid); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return c,opp,rid,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,opp,rid,None
if __name__=="__main__":
    jobs=[]
    for c,new in NEW.items():
        for s in IHS.get(c,[])[5:11]:
            jobs.append((c,s,-1,"herdsafe")); jobs.append((c,s,new,"herdsafe"))
        for s in (IR7.get(c,[])[:3]+IR7b.get(c,[])[:3]):
            jobs.append((c,s,-1,"rescue7")); jobs.append((c,s,new,"rescue7"))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"hsfix_ver.json","w"))
    per=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,opp,rid,m in res:
        if m is None: continue
        a=per[(c,opp)][rid]; a[0]+= m>0; a[1]+=1; a[2]+=m
    shared={}; hsonly={}
    for c,new in sorted(NEW.items()):
        hb,hbn,_=per[(c,"herdsafe")].get(-1,[0,0,0.0]); hn,hnn,_=per[(c,"herdsafe")].get(new,[0,0,0.0])
        rb,rbn,_=per[(c,"rescue7")].get(-1,[0,0,0.0]); rn,rnn,_=per[(c,"rescue7")].get(new,[0,0,0.0])
        okhs = hnn>=4 and hn>hb
        safer7 = rnn==0 or rn>=rb
        tag = "共享进" if (okhs and safer7) else ("仅HS行" if okhs else "弃")
        if okhs and safer7: shared[c]=new
        elif okhs: hsonly[c]=new
        print(f"[{tag:5s}] {c:30s} 带{new:4d} | herdsafe {hn}/{hnn}(基{hb}) | rescue7 {rn}/{rnn}(基{rb})")
    json.dump({"shared":shared,"hsonly":hsonly}, open(HERE/"hsfix_final.json","w"))
    print(f"共享行进 {len(shared)} 格;需独立 HS 行 {len(hsonly)} 格")
