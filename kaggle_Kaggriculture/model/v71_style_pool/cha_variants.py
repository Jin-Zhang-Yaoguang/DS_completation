"""cha 谱系变种拆分:对手第 144-431 步买畜/买种签名 → 匹配路线库最近路线;与已知代表在同商店组合下的选路对照;按队伍归类变种并统计 r38c 胜率。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
from review_fp import cls
def sig(acts):
    s=set()
    for t,a in acts:
        if not (144<=t<432): continue
        for x in ((a or {}).get("market") or []):
            if x and x[0] in ("BUY_ANIMAL","BUY_SEED"):
                try: n=int(x[2]) if len(x)>2 else 1
                except Exception: n=1
                s.add((t//24,x[0],str(x[1]),n))
    return s
def jac(a,b): return len(a&b)/max(1,len(a|b))
def rep_run(job):
    rep,seed,seat=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[rep]).parent))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54r38e_main.py"); op=fidelity.make_agent(f"sub:{OPP[rep]}")
        k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat; acts=[]
        for t in range(432):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); acts.append((t,a[o])); g.step(a[0],a[1])
        shops=tuple((g.observe(0)["town"]["unlocked_shops"] or [])[:2])
        return job,(shops,[(t,x) for t,x in acts])
    except Exception as ex: return job,None
if __name__=="__main__":
    ns={}; exec(open("agents/v54r38e_main.py").read(),ns); ROUTES=ns["_IMPL"].chassis.routes
    RS={r:sig(list(enumerate(tape))) for r,tape in ROUTES.items()}
    def best(s):
        sc=sorted(((jac(s,v),r) for r,v in RS.items()),reverse=True)
        return sc[0][1],sc[0][0]
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    REPS=["engineV3","cha22","tetsu16","demand28"]
    with ProcessPoolExecutor(8) as ex: RR=list(ex.map(rep_run,[(rp,IDX[c][0],0) for rp in REPS for c in cells],chunksize=2))
    table=collections.defaultdict(dict)
    for (rp,sd,st),v in RR:
        if v: shops,acts=v; r,s=best(sig(acts)); table[rp][shops]=(r,round(s,2))
    for rp in REPS: print(f"代表 {rp}: 选路分布 {collections.Counter(r for r,_ in table[rp].values()).most_common(6)}  平均匹配度 {sum(s for _,s in table[rp].values())/max(1,len(table[rp])):.2f}",flush=True)
    # 对手棋盘
    boards=[]
    for r in json.load(open("official_rows.json")):
        if r["cls"]=="cha谱系": boards.append(("官方",r["eid"],1-r["seat"],r["team"],r["d"],tuple(r["shops"]),"roff"))
    for e,v in json.load(open("online_games.json")).items():
        if v.get("key") and cls(float(round(v["key"][0])),v["lin"])=="cha谱系": boards.append(("线上",e,1-v["seat"],v["opp_team"],v["d"],tuple(v["shops"]),"rlive3"))
    out=[]
    for src,e,o,team,d,shops,dirn in boards:
        rr=json.load(open(HERE/dirn/f"{e}.json"))
        s=sig([(t-1,rr["acts"][t][o]) for t in range(1,len(rr["acts"]))])
        r,sc=best(s)
        match=[rp for rp in REPS if table[rp].get(shops,(None,))[0]==r]
        out.append(dict(src=src,team=team,d=d,shops=shops,route=r,score=sc,match=match))
    json.dump(out,open("cha_variants.json","w"),ensure_ascii=False)
    # 按队伍归类:该队所有局中最常匹配的代表集合
    T=collections.defaultdict(list)
    for x in out: T[x["team"]].append(x)
    lab={}
    for t,L in T.items():
        c=collections.Counter()
        for x in L:
            for rp in (x["match"] or ["未匹配"]): c[rp]+=1
        top=c.most_common(1)[0]; lab[t]=top[0] if top[1]/len(L)>=0.6 else "混合"
    V=collections.defaultdict(lambda:[0,0,0.0,set()])
    for x in out:
        a=V[lab[x["team"]]]; a[0]+=1; a[1]+=x["d"]>0; a[2]+=x["d"]; a[3].add(x["team"])
    print(f"\ncha 对手棋盘 {len(out)}(路线签名平均匹配度 {sum(x['score'] for x in out)/len(out):.2f}),按队伍归入变种:")
    for k,a in sorted(V.items(),key=lambda kv:-kv[1][0]):
        print(f"   {k:8s} 棋盘 {a[0]:4d} 队伍 {len(a[3]):3d}  r38c/我方 胜 {a[1]}/{a[0]} ({a[1]/a[0]:.0%}) 均差 {a[2]/a[0]:6.0f}")
    print("\n对手实际选路(全部 cha 棋盘)前 10:",collections.Counter(x["route"] for x in out).most_common(10))
