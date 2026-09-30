"""三项回归门控(通用):NEW vs 基线 r34 / r38c。
A 双席位大种子 × 8 最强代表;B 官方回放开环(全部动物优先开局盘 + 600 随机盘,两席位已含);B2 我方最近5天动物优先开局对局开环;C 双席位直接对打。"""
import json, random, collections, os, sys, glob, datetime
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
from official_eval import sim
NEW=sys.argv[1]; BASES=["v54r34","v54r38c"]; ALL=[NEW]+BASES
OPPS=["me2965_28","guru28","harvest88","engineV3","rescue7","metav4","v52","fieldcraft29"]
W=int(os.environ.get("KAG_WORKERS","8"))
def pr(*a): print(*a,flush=True)
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    # A
    jobs=[(v,o,IDX[c][2],st,f"{v}|{o}|{c}|{st}",()) for v in ALL for o in OPPS for c in cells for st in (0,1)]
    with ProcessPoolExecutor(W) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    pr("[A 双席位大种子 × 8 最强代表] 胜/128")
    tot=collections.Counter(); td=collections.Counter()
    for o in OPPS:
        line=f"   {o:12s}"
        for v in ALL:
            d=[R.get(f"{v}|{o}|{c}|{st}") for c in cells for st in (0,1)]; d=[x for x in d if x is not None]
            tot[v]+=sum(x>0 for x in d); td[v]+=sum(d); line+=f"  {v[3:]}: {sum(x>0 for x in d):3d} ({sum(d)/max(1,len(d)):5.0f})"
        pr(line)
    pr("   合计 "+"  ".join(f"{v[3:]}: {tot[v]}/1024 均{td[v]/1024:.0f}" for v in ALL))
    # B
    rows=json.load(open("official_rows.json")); random.seed(7); S=random.sample(rows,600)
    keys={(r["eid"],r["seat"]) for r in S}; S+= [r for r in rows if r["cls"]=="Majkel簇" and (r["eid"],r["seat"]) not in keys]
    jobs=[(v,"roff",r["eid"],r["seat"],()) for v in (NEW,"v54r34") for r in S]
    with ProcessPoolExecutor(W) as ex: X=dict(ex.map(sim,jobs,chunksize=2))
    G=collections.defaultdict(lambda:collections.defaultdict(list))
    for r in S:
        vals={"v54r38c":r["d"]}
        for v in (NEW,"v54r34"):
            x=X.get((v,"roff",r["eid"],r["seat"],()))
            if x: vals[v]=x["d"]
        if len(vals)<3: continue
        for g in (r["cls"],"合计(含全部动物优先盘)"):
            for v in ALL: G[g][v].append(vals[v])
    pr(f"\n[B 官方回放开环 {len(S)} 盘] 胜 (均差)")
    for c,g in sorted(G.items(),key=lambda kv:-len(kv[1][NEW])):
        pr(f"   {c:22s} n={len(g[NEW]):4d} "+"  ".join(f"{v[3:]}: {sum(x>0 for x in g[v]):4d} ({sum(g[v])/max(1,len(g[v])):6.0f})" for v in ALL))
    # B2
    m=json.load(open("meta_live.json")); H=json.load(open("rkey_head.json"))
    SINCE=(datetime.datetime.now(datetime.UTC)-datetime.timedelta(days=5)).strftime("%Y-%m-%dT%H")
    own=[(e,v) for e,v in m.items() if (v.get("end") or "")>=SINCE and (H.get(e) or {}).get("rkey") and 460<=H[e]["rkey"][0]<=650 and os.path.exists(f"rlive3/{e}.json") and v.get("opp")]
    jobs=[(v,"rlive3",e,json.load(open(f"rlive3/{e}.json"))["seat"],()) for v in ALL for e,_ in own]
    with ProcessPoolExecutor(W) as ex: Y=dict(ex.map(sim,jobs,chunksize=1))
    pr(f"\n[B2 我方最近5天 动物优先开局对局开环 {len(own)} 盘] 胜 (均差),按对手分段")
    for lvl,flt in (("全部",lambda v:True),("≥2000",lambda v:v["opp"]["initialScore"]>=2000),("<2000",lambda v:v["opp"]["initialScore"]<2000)):
        T=[(e,v) for e,v in own if flt(v)]
        line=f"   {lvl:6s} n={len(T):3d}"
        for a in ALL:
            d=[(Y.get((a,"rlive3",e,json.load(open(f"rlive3/{e}.json"))["seat"],())) or {}).get("d") for e,_ in T]; d=[x for x in d if x is not None]
            line+=f"  {a[3:]}: {sum(x>0 for x in d):3d} ({sum(d)/max(1,len(d)):6.0f})"
        pr(line)
    # C
    for base in BASES:
        jobs=[(NEW,base,IDX[c][i],st,f"{c}|{i}|{st}",()) for c in cells for i in (0,1) for st in (0,1)]
        with ProcessPoolExecutor(W) as ex: Z=[d for _,d in ex.map(be.one,jobs,chunksize=2) if d is not None]
        pr(f"\n[C 双席位直接对打] {NEW[3:]} vs {base[3:]} {len(Z)} 局: 胜 {sum(x>0 for x in Z)} 平 {sum(x==0 for x in Z)} 负 {sum(x<0 for x in Z)} 均差 {sum(Z)/max(1,len(Z)):.0f}")
