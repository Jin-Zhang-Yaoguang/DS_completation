import json,os,collections
IDX=json.load(open("online_games.json"))
L=[e for e,v in IDX.items() if v["ver"]=="v55b" and v["d"]<0]
def pre(acts,q,T): return json.dumps([a[q] for a in acts[1:T]])
# 参考库:官方回放(两席)
lib=collections.defaultdict(list)
for d in ("roff_af","roff"):
    for f in os.listdir(d):
        try: r=json.load(open(f"{d}/{f}"))
        except: continue
        for q in (0,1): lib[pre(r["acts"],q,40)].append((r["names"][q],r["eid"]))
for e in L:
    r=json.load(open(f"rlive3/{e}.json")); o=1-r["seat"]
    k=pre(r["acts"],o,40); hit=lib.get(k,[])
    print(e,IDX[e]["opp_team"],"前40步完全相同的官方回放:",len(hit),collections.Counter(n for n,_ in hit).most_common(6))
# 三个负局对手之间的相同前缀长度
R={e:json.load(open(f"rlive3/{e}.json")) for e in L}
def same(a,b):
    ra,rb=R[a],R[b];oa,ob=1-ra["seat"],1-rb["seat"];t=0
    while t<min(len(ra["acts"]),len(rb["acts"])) and ra["acts"][t][oa]==rb["acts"][t][ob]: t+=1
    return t
for i in range(len(L)):
    print(L[i],IDX[L[i]]["opp_team"][:12],[same(L[i],L[j]) for j in range(len(L))])
