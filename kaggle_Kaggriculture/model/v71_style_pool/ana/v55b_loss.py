import json,collections
IDX=json.load(open("online_games.json"))
G=sorted([(v["end"],e,v) for e,v in IDX.items() if v["ver"]=="v55b"])
def prof(acts,q):
    buy=collections.Counter(); sell=collections.Counter(); first=None; land=0; hire=0
    for t,a in enumerate(acts):
        a=a[q] or {}
        for m in a.get("market") or []:
            if not m: continue
            k=m[0]
            if k=="BUY_ANIMAL": buy[m[1]]+=m[2] if len(m)>2 else 1
            elif k=="SELL_PRODUCT" or k=="SELL": sell[m[1]]+=m[2] if len(m)>2 else 1
            elif k=="BUY_LAND": land+=1
            elif k=="HIRE": hire+=1
            if first is None and k=="BUY_ANIMAL": first=t
    return buy,sell,first,land,hire
for end,e,v in G:
    if v["d"]>=0: continue
    r=json.load(open(f"rlive3/{e}.json")); s=r["seat"]; o=1-s; M=r["money"]; A=r["acts"]
    print("="*100); print(e,v["opp_team"],"d",v["d"],"seat",s,"key",v["key"],"shops",r["shops"])
    print(" 对手step1 market:",(A[1][o] or {}).get("market"))
    cur=[t for t in (72,144,216,288,360,432,504,576,len(M)-2) if t<len(M) and M[t]]
    print(" 金币(我/对手/差):"," ".join(f"t{t}:{M[t][s]:.0f}/{M[t][o]:.0f}/{M[t][s]-M[t][o]:+.0f}" for t in cur))
    for nm,q in (("我",s),("对手",o)):
        b,se,f,la,hi=prof(A,q)
        print(f" {nm}: 首次买畜t{f} 买畜{dict(b)} 买地{la}\n     卖:{dict(se.most_common(9))}")
