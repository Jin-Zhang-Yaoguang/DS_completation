"""指纹复查(最近 5 天):A 识别准确(代表保真 + 类内行为一致) / B 针对有效(r38c 开 vs 关 该类针对表,代表闭环 + 对手实录开环)。"""
import sys, os, json, glob, collections, datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
K42=1042.0
def cls(key,lin):
    if key==K42 and lin=="cha": return "cha谱系"
    if key==K42: return "新版人群"
    if key in (1039.0,1041.0,1043.0): return "rescue7系"
    if key==151.0: return "K52"
    if key==1049.0: return "metav4"
    if 460<=key<=650: return "Majkel簇"
    if key<900: return "其他低现金"
    return "其他键"
REP={"新版人群":"me2965_28","cha谱系":"engineV3","rescue7系":"rescue7","K52":"v52","metav4":"metav4"}
OFF={"新版人群":"NG","cha谱系":"CHA","rescue7系":"R7","K52":"K52","metav4":"MV4","Majkel簇":"MAJ"}
def one(job):
    agent,opp,eid,env=job
    os.environ.pop("KAG_CUTOFF",None)
    for kv in env: k,v=kv.split("=",1); os.environ[k]=v
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(HERE/f"rlive3/{eid}.json")); seat=r["seat"]; o=1-seat
        if opp=="TAPE": op=fidelity.tape_agent([r["acts"][t+1][o] for t in range(len(r["acts"])-1)])
        else: sys.path.insert(0,str(Path(OPP[opp]).parent)); op=fidelity.make_agent(f"sub:{OPP[opp]}")
        me=fidelity.make_agent(f"sub:{HERE}/agents/{agent}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=r["seed"])
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return job,float(g.reward(seat)-g.reward(o))
    except Exception: return job,None
def behav(r):
    o=1-r["seat"]; c=collections.Counter(); first=None
    for t in range(1,min(300,len(r["acts"]))):
        for x in ((r["acts"][t][o] or {}).get("market") or []):
            if x and x[0]=="BUY_ANIMAL":
                try: n=int(x[2]) if len(x)>2 else 1
                except Exception: n=1
                c[str(x[1])]+=n; first=first or t
            if x and x[0]=="BUY_LAND": c["LAND"]+=1
    return f"羊{c['SHEEP']}牛{c['COW']}鹅{c['GOOSE']}地{c['LAND']}", first
if __name__=="__main__":
    W=int(os.environ.get("KAG_WORKERS","8")); CAP=int(os.environ.get("CAP","60"))
    m=json.load(open("meta_live.json")); H=json.load(open("rkey_head.json"))
    SINCE=(datetime.datetime.utcnow()-datetime.timedelta(days=5)).strftime("%Y-%m-%dT%H")
    ns={}; exec(open("agents/v54r38c_main.py").read(),ns)
    def hit(c,shops):
        t=lambda n: shops in ns[n]
        if c=="新版人群": return t("_R36_MILK") or t("_R32_NEWGEN") or t("_R33_NEWGEN_LATE")
        if c=="cha谱系": return t("_R38_CHA") or shops in ns["_R23_CHA"][(K42,9989)] or t("_R33_CHA_LATE")
        if c=="rescue7系": return t("_R28_MILK39") or t("_R21_MIR") or t("_R20_SPLICE")
        if c=="K52": return t("_R21_K52") or t("_V54R3_K52")
        if c=="metav4": return t("_R22_MV4")
        return c=="Majkel簇"
    B=[]
    for e,v in sorted(m.items(),key=lambda kv:kv[1].get("end") or "",reverse=True):
        if (v.get("end") or "")<SINCE or not v.get("opp") or v["opp"].get("reward") is None or v["me"].get("reward") is None: continue
        f=HERE/f"rlive3/{e}.json"; hk=(H.get(e) or {}).get("rkey")
        if not f.exists() or not hk: continue
        r=json.load(open(f)); o=1-r["seat"]; Mo=r["money"]; lin="cha" if (Mo[92] and Mo[91] and Mo[92][o]-Mo[91][o]>50) else "main"
        c=cls(float(hk[0]),lin); shops=tuple((r.get("shops") or [])[:2])
        B.append(dict(eid=e,ver=("r38" if v["ver"]=="r38b" else v["ver"]),cls=c,d=v["me"]["reward"]-v["opp"]["reward"],opp=v["opp"]["initialScore"],hit=hit(c,shops),beh=behav(r)))
    print(f"窗口 {SINCE} 起,有回放+指纹 {len(B)} 局:",dict(collections.Counter(x["cls"] for x in B)),flush=True)
    # A2 类内行为一致性
    print("\n[A2 类内行为(对手前 300 步买畜/买地)]")
    for c in REP.keys()|{"Majkel簇","其他低现金","其他键"}:
        S=[x for x in B if x["cls"]==c]
        if not S: continue
        sig=collections.Counter(x["beh"][0] for x in S).most_common(3); fs=sorted(x["beh"][1] or 999 for x in S)
        print(f"  {c:10s} n={len(S):3d} 首次买畜步中位 {fs[len(fs)//2]:4d}  前三签名 "+"  ".join(f"{s}:{k/len(S):.0%}" for s,k in sig))
    # A1 代表保真
    print("\n[A1 代表保真:实际参赛版本 vs 代表,模拟胜负与线上一致率]",flush=True)
    jobs=[]; pick={}
    for c,rep in REP.items():
        S=[x for x in B if x["cls"]==c][:CAP]; pick[c]=S
        jobs+= [(f"v54{x['ver']}",rep,x["eid"],()) for x in S]
    with ProcessPoolExecutor(W) as ex: R=dict(ex.map(one,jobs,chunksize=1))
    for c,rep in REP.items():
        S=pick[c]; ok=sum(1 for x in S if R.get((f"v54{x['ver']}",rep,x["eid"],())) is not None and (R[(f"v54{x['ver']}",rep,x["eid"],())]>0)==(x["d"]>0))
        lw=sum(1 for x in S if x["d"]<0 and (R.get((f"v54{x['ver']}",rep,x["eid"],())) or 1)<0)
        if S: print(f"  {c:10s} 代表 {rep:10s} 一致 {ok}/{len(S)} ({ok/len(S):.0%})  线上败局复现 {lw}/{sum(x['d']<0 for x in S)}",flush=True)
    # B 针对有效性
    print("\n[B 针对有效:r38c 开 vs 关 该类针对表(只看命中局)]",flush=True)
    for c,off in OFF.items():
        S=[x for x in B if x["cls"]==c and x["hit"]][:CAP]
        if not S: print(f"  {c}: 无命中局"); continue
        for opp in ([REP[c],"TAPE"] if c in REP else ["TAPE"]):
            j1=[("r38abl",opp,x["eid"],()) for x in S]; j0=[("r38abl",opp,x["eid"],(f"KAG_CUTOFF={off}",)) for x in S]
            with ProcessPoolExecutor(W) as ex: R1=dict(ex.map(one,j1,chunksize=1)); R0=dict(ex.map(one,j0,chunksize=1))
            for lvl,flt in (("全部",lambda x:True),("≥2000",lambda x:x["opp"]>=2000)):
                T=[x for x in S if flt(x) and R1.get(("r38abl",opp,x["eid"],())) is not None and R0.get(("r38abl",opp,x["eid"],(f"KAG_CUTOFF={off}",))) is not None]
                if not T: continue
                a=[R1[("r38abl",opp,x["eid"],())] for x in T]; b=[R0[("r38abl",opp,x["eid"],(f"KAG_CUTOFF={off}",))] for x in T]
                print(f"  {c:10s} vs {opp:10s} {lvl:5s} n={len(T):3d}  开 胜{sum(v>0 for v in a):3d} 均{sum(a)/len(T):7.0f} | 关 胜{sum(v>0 for v in b):3d} 均{sum(b)/len(T):7.0f} | 翻盘 +{sum(1 for p,q in zip(a,b) if p>0>=q)} −{sum(1 for p,q in zip(a,b) if q>0>=p)}",flush=True)
