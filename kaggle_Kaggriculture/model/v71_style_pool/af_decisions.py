"""动物优先开局目标队伍决策点分析 + "是否针对固定带"检验。"""
import json, glob, collections, statistics as st
from review_fp import cls
TEAMS=["Luca","Aaweg","Planned Economy","Arjun Vinod","high frequency farming","Alan C52","daulettoibazar","pangzi233","DeeperNet","Vlas Veles","tine.sh agent"]
PREM=("CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER")
FIXED={"新版人群","cha谱系","rescue7系","metav4","K52"}
def n_of(x):
    try: return int(x[2]) if len(x)>2 else 1
    except Exception: return 1
recs=[]
for f in glob.glob("roff_af/*.json"):
    r=json.load(open(f)); nm=r["names"]
    seats=[i for i,n in enumerate(nm) if n in TEAMS]
    for p in seats:
        o=1-p; M=r["money"]
        sk=r["key2"][o]   # 对手视角看到的目标方 t2 现金/小麦 = 目标自己的开局键
        if not (sk[1] in (9990,9991,9992) and sk[0]<900): continue
        k=r["key2"][p]; lin="cha" if (M[92] and M[91] and M[92][o]-M[91][o]>50) else "main"
        oc=cls(float(round(k[0])),lin); okind="固定路线型" if oc in FIXED else ("动物优先" if (k[1] in (9990,9991,9992) and k[0]<900) else "其他")
        day=collections.defaultdict(collections.Counter); sells=[collections.defaultdict(list),collections.defaultdict(list)]
        for t in range(1,len(r["acts"])):
            d=(t-1)//24
            for i,side in ((0,p),(1,o)):
                for x in ((r["acts"][t][side] or {}).get("market") or []):
                    if not x: continue
                    if x[0]=="SELL" and x[1] in PREM: sells[i][x[1]].append(t)
                    if i==0:
                        if x[0]=="HIRE": day[d]["hire"]+=1
                        elif x[0]=="BUY_LAND": day[d]["land"]+=1
                        elif x[0]=="BUY_ANIMAL": day[d]["ani_"+x[1]]+=n_of(x)
                        elif x[0]=="BUY_SEED": day[d]["seed_"+x[1]]+=n_of(x)
                        elif x[0]=="SELL": day[d]["sell_"+x[1]]+=n_of(x)
                        elif x[0]=="BUY_PRODUCT": day[d]["buy_"+x[1]]+=n_of(x)
        # 抢先卖:我方每次卖 X,对手在之后 1-3 步内也卖 X 的比例(我在前) vs 对手在之前 1-3 步卖(我在后)
        before=after=tot=0
        for it in PREM:
            os_=set(sells[1][it])
            for t in sells[0][it]:
                tot+=1
                if any(t+k in os_ for k in (1,2,3)): before+=1
                if any(t-k in os_ for k in (1,2,3)): after+=1
        win=r["rewards"][p]>r["rewards"][o]
        recs.append(dict(team=nm[p],okind=okind,ocls=oc,win=win,day={d:dict(c) for d,c in day.items()},before=before,after=after,tot=tot,shops=r["shops"],money=[m[p] if m else None for m in M]))
json.dump(recs,open("af_decisions.json","w"),ensure_ascii=False)
print("目标队伍对局",len(recs),"对手类型",dict(collections.Counter(x["okind"] for x in recs)))
print("\n[胜率与抢先卖] 按对手类型")
for k in ("固定路线型","动物优先","其他"):
    S=[x for x in recs if x["okind"]==k]
    if not S: continue
    b=sum(x["before"] for x in S); a=sum(x["after"] for x in S); t=sum(x["tot"] for x in S)
    print(f"   vs {k:6s} 局 {len(S):4d} 胜率 {sum(x['win'] for x in S)/len(S):.0%} | 我卖后 1-3 步对手也卖(我抢先) {b/t:.1%}  对手卖后 1-3 步我才卖 {a/t:.1%}")
def agg(S,d,key): return st.mean([x["day"].get(str(d),x["day"].get(d,{})).get(key,0) for x in S]) if S else 0
print("\n[逐天决策] 所有目标队伍 均值(对固定路线型 / 对其他)")
F=[x for x in recs if x["okind"]=="固定路线型"]; O=[x for x in recs if x["okind"]!="固定路线型"]
keys=["hire","land","ani_COW","ani_SHEEP","ani_GOOSE","seed_MELON","seed_STRAWBERRY","seed_TOMATO","seed_CARROT","seed_WHEAT"]
print("   天 | "+" | ".join(k.replace("ani_","").replace("seed_","种") for k in keys))
for d in list(range(0,8))+[9,12,15,18,21,24,27]:
    print(f"   {d:2d} | "+" | ".join(f"{agg(F,d,k):4.1f}/{agg(O,d,k):4.1f}" for k in keys))
print("\n[整局卖出件数] 对固定路线型 / 对其他")
for it in PREM+("WHEAT",):
    f=st.mean([sum(v.get("sell_"+it,0) for v in x["day"].values()) for x in F]); o_=st.mean([sum(v.get("sell_"+it,0) for v in x["day"].values()) for x in O])
    print(f"   {it:10s} {f:7.0f} / {o_:7.0f}")
