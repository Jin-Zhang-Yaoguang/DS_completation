"""官方回放复盘(最近 5 天):r38c 顶替任一方,对手按实录动作开环。
指标:1) 指纹命中覆盖 2) 各指纹反制带开/关胜率 3) 其他轴(整体胜率/分差、对真实赢家与输家、各类未命中表现)
校准:我方自身对局上 开环结果 vs 线上结果 一致率(按类),判断开环可信度。"""
import sys, os, json, glob, collections, datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from review_fp import cls, OFF
K42=1042.0
def sim(job):
    agent,src,eid,seat,env=job
    os.environ.pop("KAG_CUTOFF",None)
    for kv in env: k,v=kv.split("=",1); os.environ[k]=v
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(HERE/src/f"{eid}.json")); o=1-seat
        op=fidelity.tape_agent([r["acts"][t+1][o] for t in range(len(r["acts"])-1)])
        me=fidelity.make_agent(f"sub:{HERE}/agents/{agent}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=r["seed"]); t=0; key=None; m91=None; lin="main"
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]
            if t==2: key=(float(obs[seat]["farms"][o]["money"]),int(obs[seat]["market"]["inventory"]["WHEAT"]))
            if t==91: m91=float(obs[seat]["farms"][o]["money"])
            if t==92 and m91 is not None and float(obs[seat]["farms"][o]["money"])-m91>50: lin="cha"
            a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1]); t+=1
        return job,dict(d=float(g.reward(seat)-g.reward(o)),key=key,lin=lin)
    except Exception as ex: return job,None
if __name__=="__main__":
    W=int(os.environ.get("KAG_WORKERS","8")); CAP=int(os.environ.get("CAP","150"))
    ns={}; exec(open("agents/v54r38c_main.py").read(),ns)
    def hit(c,shops):
        t=lambda n: shops in ns[n]
        if c=="新版人群": return t("_R36_MILK") or t("_R32_NEWGEN") or t("_R33_NEWGEN_LATE")
        if c=="cha谱系": return t("_R38_CHA") or shops in ns["_R23_CHA"][(K42,9989)] or t("_R33_CHA_LATE")
        if c=="rescue7系": return t("_R28_MILK39") or t("_R21_MIR") or t("_R20_SPLICE")
        if c=="K52": return t("_R21_K52") or t("_V54R3_K52")
        if c=="metav4": return t("_R22_MV4")
        return c=="Majkel簇"
    def kcls(key,lin):
        return cls(float(round(key[0])),lin) if key else "其他键"
    # ---- 校准:我方自身最近 5 天对局 ----
    SINCE=(datetime.datetime.now(datetime.UTC)-datetime.timedelta(days=5)).strftime("%Y-%m-%dT%H")
    mm=json.load(open("meta_live.json"))
    own=[(e,v) for e,v in mm.items() if (v.get("end") or "")>=SINCE and v["ver"] in ("r34","r36","r38","r38b") and (HERE/f"rlive3/{e}.json").exists() and v.get("opp") and v["opp"].get("reward") is not None]
    own=sorted(own,key=lambda ev:ev[1]["end"],reverse=True)[:int(os.environ.get("CAL","300"))]
    jobs=[(("v54r38" if v["ver"]=="r38b" else f"v54{v['ver']}"),"rlive3",e,json.load(open(HERE/f"rlive3/{e}.json"))["seat"],()) for e,v in own]
    with ProcessPoolExecutor(W) as ex: RC=dict(ex.map(sim,jobs,chunksize=1))
    cal=collections.defaultdict(lambda:[0,0,0,0])
    for j,(e,v) in zip(jobs,own):
        x=RC.get(j)
        if not x: continue
        c=kcls(x["key"],x["lin"]); on=v["me"]["reward"]-v["opp"]["reward"]
        a=cal[c]; a[0]+=1; a[1]+=(x["d"]>0)==(on>0); a[2]+=x["d"]>0; a[3]+=on>0
    print("[校准] 我方自身对局:开环复现 vs 线上(按类)  —— 一致率越高,该类开环结论越可信")
    for c,a in sorted(cal.items(),key=lambda kv:-kv[1][0]): print(f"   {c:10s} n={a[0]:3d} 一致 {a[1]/a[0]:4.0%}  开环胜 {a[2]}  线上胜 {a[3]}")
    # ---- 官方回放 ----
    files=sorted(glob.glob(str(HERE/"roff/*.json")))
    boards=[]
    for f in files:
        r=json.load(open(f))
        if "datatuu" in r["names"]: continue
        for s in (0,1): boards.append((r["eid"],s,r["names"][1-s],(r["rewards"][1-s] or 0)>(r["rewards"][s] or 0),tuple((r.get("shops") or [])[:2])))
    print(f"\n官方回放 {len(files)} 局 → 棋盘 {len(boards)}(r38c 分别顶替两方)",flush=True)
    jobs=[("v54r38c","roff",e,s,()) for e,s,_,_,_ in boards]
    with ProcessPoolExecutor(W) as ex: R=dict(ex.map(sim,jobs,chunksize=2))
    rows=[]
    for (e,s,team,opp_won,shops),j in zip(boards,jobs):
        x=R.get(j)
        if not x: continue
        c=kcls(x["key"],x["lin"]); rows.append(dict(eid=e,seat=s,team=team,opp_won=opp_won,shops=shops,cls=c,hit=hit(c,shops),d=x["d"],key=x["key"]))
    json.dump(rows,open("official_rows.json","w"),ensure_ascii=False)
    n=len(rows); cov=sum(r["cls"] not in ("其他低现金","其他键") for r in rows)
    print(f"\n[1 指纹覆盖] 有效棋盘 {n}:落入已建指纹类 {cov} ({cov/n:.0%});触发专属针对格 {sum(r['hit'] for r in rows)} ({sum(r['hit'] for r in rows)/n:.0%})")
    S=collections.defaultdict(lambda:collections.Counter())
    for r in rows:
        a=S[r["cls"]]; a["n"]+=1; a["h"]+=r["hit"]; a["w"]+=r["d"]>0; a["hw"]+=r["hit"] and r["d"]>0; a["d"]+=r["d"]; a["tw"]+=r["opp_won"]; a["tww"]+=r["opp_won"] and r["d"]>0
    teams=collections.defaultdict(set)
    for r in rows: teams[r["cls"]].add(r["team"])
    print(f"   {'类别':10s} {'棋盘':>5s} {'占比':>5s} {'队伍':>4s} {'命中格':>7s}")
    for c,a in sorted(S.items(),key=lambda kv:-kv[1]["n"]): print(f"   {c:10s} {a['n']:5d} {a['n']/n:5.0%} {len(teams[c]):4d} {a['h']/a['n']:7.0%}")
    # ---- 2 反制带开/关 ----
    print("\n[2 反制带有效性:命中局 r38c 开 vs 关该类针对表]",flush=True)
    for c,off in OFF.items():
        T=[r for r in rows if r["cls"]==c and r["hit"]][:CAP]
        if not T: print(f"   {c}: 无命中"); continue
        j0=[("r38abl","roff",r["eid"],r["seat"],(f"KAG_CUTOFF={off}",)) for r in T]
        with ProcessPoolExecutor(W) as ex: R0=dict(ex.map(sim,j0,chunksize=1))
        b=[(R0.get(j) or {}).get("d") for j in j0]; P=[(r["d"],q) for r,q in zip(T,b) if q is not None]
        print(f"   {c:10s} n={len(P):3d} 开 胜{sum(p>0 for p,_ in P):4d} ({sum(p>0 for p,_ in P)/len(P):.0%}) 均{sum(p for p,_ in P)/len(P):7.0f} | 关 胜{sum(q>0 for _,q in P):4d} ({sum(q>0 for _,q in P)/len(P):.0%}) 均{sum(q for _,q in P)/len(P):7.0f} | 翻盘 +{sum(1 for p,q in P if p>0>=q)} −{sum(1 for p,q in P if q>0>=p)}",flush=True)
    # ---- 3 其他轴 ----
    print("\n[3 其他轴:r38c 整体(方向0 通用实力)]")
    for c,a in sorted(S.items(),key=lambda kv:-kv[1]["n"]):
        print(f"   {c:10s} 胜 {a['w']:4d}/{a['n']:<4d} {a['w']/a['n']:4.0%} 均差 {a['d']/a['n']:7.0f} | 对实际赢家 {a['tww']}/{a['tw']} | 命中胜 {a['hw']}/{a['h']} 未命中胜 {a['w']-a['hw']}/{a['n']-a['h']}")
    W_=sum(r["d"]>0 for r in rows); tw=[r for r in rows if r["opp_won"]]
    print(f"   合计 胜 {W_}/{n} {W_/n:.0%}  对实际赢家 {sum(r['d']>0 for r in tw)}/{len(tw)}  败局均差 {sum(r['d'] for r in rows if r['d']<0)/max(1,n-W_):.0f}  近失(<2k)败局 {sum(1 for r in rows if -2000<r['d']<0)}")
