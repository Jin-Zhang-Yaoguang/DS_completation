"""轴5 执行层消融:r26base 各层单独关闭。评测:新公开对手(10×64)、rlive3 真实动作带(256)、老对手(6×64)。
用法: python exec_ablate.py <tag> <变体;变体;...>   变体=逗号分隔的关闭层,"-"=全开
输出 exec_ablate_<tag>.json(逐局)"""
import sys, os, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from bench_pub import OPPS as PUB
IDX=json.load(open(HERE/os.environ.get("ABL_INDEX","combo_index3.json")))["v54"]
SI=int(os.environ.get("ABL_SEED","0"))
PUBO=os.environ.get("ABL_PUBO","harvestledger,hybrid2965,engineV3,shepledger,godsmode,idleseller,pipe18,v40chal,v57fo,poprobust").split(",")
OLDO=["v54","v56","rescue7","v52","metav4","herdsafe"]
AGENT=os.environ.get("ABL_AGENT","v54r26base")
def opp_path(o): return str(PUB[o]) if o in PUB else str(HERE/f"agents/{o}_main.py")
def one(job):
    var,kind,a,b=job
    off,on,moff,mfrom=[],[],[],"0"
    for part in ([] if var=="-" else var.split("|")):
        if part.startswith("+"): on+=part[1:].split(",")
        elif part.startswith("M:"):
            body=part[2:]; body,_,mf=body.partition("@"); moff+=body.split(","); mfrom=mf or "0"
        else: off+=part.split(",")
    os.environ["KAG_EXEC_OFF"]=",".join(off); os.environ["KAG_EXEC_ON"]=",".join(on); os.environ["KAG_EXEC_OFF_MILK"]=",".join(moff); os.environ["KAG_MILK_FROM"]=mfrom
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{AGENT}_main.py")
        if kind=="live3":
            r=json.load(open(a)); seat=r["seat"]; o=1-seat
            op=fidelity.tape_agent([r["acts"][t+1][o] for t in range(len(r["acts"])-1)]); seed=r["seed"]
        else:
            sys.path.insert(0,str(Path(opp_path(a)).parent)); op=fidelity.make_agent(f"sub:{opp_path(a)}"); seat,o,seed=0,1,b[1]
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; x=[None,None]; x[seat]=me(obs[seat]); x[o]=op(obs[o]); g.step(x[0],x[1])
        return var,kind,(Path(a).stem if kind=="live3" else a),(None if kind=="live3" else b[0]),float(g.reward(seat)-g.reward(o))
    except Exception as e: return var,kind,str(a),None,None
if __name__=="__main__":
    tag=sys.argv[1]; vars_=sys.argv[2].split(";"); sets=os.environ.get("ABL_SETS","pub,live3,old").split(",")
    MILK={"PIZZA_SHOP","ICE_CREAM_SHOP","SMOOTHIE_SHOP"}
    only_milk=os.environ.get("ABL_MILK")=="1"
    okc=lambda c: (not only_milk) or bool(MILK & set(c.split("|")))
    f3=[f for f in sorted(glob.glob(str(HERE/"rlive3/*.json"))) if (not only_milk) or bool(MILK & set((json.load(open(f)).get("shops") or [])[:2]))][:int(os.environ.get("ABL_LIVE_N","100000"))]
    jobs=[]
    for v in vars_:
        if "pub" in sets: jobs+=[(v,"pub",o,(c,s[min(SI,len(s)-1)])) for o in PUBO for c,s in sorted(IDX.items()) if okc(c)]
        if "old" in sets: jobs+=[(v,"old",o,(c,s[min(SI,len(s)-1)])) for o in OLDO for c,s in sorted(IDX.items()) if okc(c)]
        if "live3" in sets: jobs+=[(v,"live3",f,None) for f in f3]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump(res,open(HERE/f"exec_ablate_{tag}.json","w"))
    A=collections.defaultdict(lambda:[0,0,0.0])
    for v,kind,o,c,m in res:
        if m is None: continue
        a=A[(v,kind)]; a[0]+=m>0; a[1]+=1; a[2]+=m
    base={k:A[("-",k)] for k in ("pub","live3","old")}
    print(f"{'变体(关闭层)':16s} "+"  ".join(f"{k:>18s}" for k in ("pub","live3","old"))+"   合计胜差")
    for v in vars_:
        tot=sum(A[(v,k)][0]-base[k][0] for k in base if A[(v,k)][1])
        print(f"{v:16s} "+"  ".join(f"{A[(v,k)][0]:4d}/{A[(v,k)][1]:3d}({A[(v,k)][2]/max(1,A[(v,k)][1]):+6.0f})" for k in ("pub","live3","old"))+f"   {tot:+d}")
