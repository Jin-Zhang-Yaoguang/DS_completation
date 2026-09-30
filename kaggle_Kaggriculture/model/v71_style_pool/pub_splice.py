"""新公开对手选带粗筛:64 组合 × {r22默认, t144/t288/t360/t432 × 13 带} × 新对手 × 1 seed(combo_index3 第 2 个种子)。
用法: python pub_splice.py <输出tag> <opp1,opp2> [seed序号]"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from bench_pub import OPPS as PUB
OPP={**{k:str(v) for k,v in PUB.items()}, **{k:str(HERE/f"agents/{k}_main.py") for k in ("rescue7","herdsafe","v54","v56","metav4","v52","hai2965","guru_v4","op_o10_5","op_o6_1","op_o5_0","op_o8_3","op_o7_2","herdsafe_vq","hs_exec","hsxA","hsxB","hsxC","hsxD","op_o10_10","op_o15_10","op_o13_8","op_o8_8","op_o20_15","op_o5_5","op_o2_1","guru29","harvest29","multiroute29","me2965_28","guru28","demand28","harvest28","cha22","engineV3","chahyb","fieldcraft29","harvest88","tetsu16","v54r34","v54r38c","v54r38e","shep29","gurutop2","hyb2965","wheatseller","ttv1","afrep_deepernet","afrep_planned","afrep_arjun","v54r38g","v54r38f","v55a","v55b","v55c","v55x","v55d","v55e","v55f","v55fa","v55fb","v55y","v55g")}}
IDX=json.load(open(HERE/os.environ.get("PUB_INDEX","combo_index3.json")))["v54"]
SHORT=[0,100,101,103,107,110,112,115,118,120,123,124,126]
ARMS=[(None,-1)]+[(c,r) for c in (144,288,360,432) for r in SHORT]
def one(job):
    c,opp,seed,cut,rid=job
    for k in list(os.environ):
        if k.startswith("KAG_CUT") or k.startswith("KAG_FORCE"): os.environ.pop(k,None)
    if cut: os.environ[f"KAG_CUT{cut}"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    sys.path.insert(0,str(Path(OPP[opp]).parent))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{os.environ.get('PROBE','r22cut')}_main.py")
        op=fidelity.make_agent(f"sub:{OPP[opp]}")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return c,opp,seed,cut,rid,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,opp,seed,cut,rid,None
if __name__=="__main__":
    tag=sys.argv[1]; opps=sys.argv[2].split(","); si=int(sys.argv[3]) if len(sys.argv)>3 else 1
    jobs=[(c,o,s[min(si,len(s)-1)],cut,rid) for c,s in sorted(IDX.items()) for o in opps for cut,rid in ARMS]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/f"pub_splice_{tag}.json","w"))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,o,s,cut,rid,m in res:
        if m is None: continue
        a=agg[c][(cut,rid)]; a[0]+=m>0; a[1]+=1; a[2]+=m
    n_imp=0
    for c in sorted(agg):
        rows=agg[c]; b=rows[(None,-1)]
        (cut,rid),(w,n,mm)=max(rows.items(),key=lambda kv:(kv[1][0],kv[1][2]))
        imp=cut is not None and w>b[0]; n_imp+=imp
        print(f"[{'改' if imp else '  '}] {c:32s} 默认 {b[0]}/{b[1]}({b[2]/max(1,b[1]):+6.0f}) -> t{cut} 带{rid} {w}/{n}({mm/max(1,n):+6.0f})")
    print("可改格",n_imp)
