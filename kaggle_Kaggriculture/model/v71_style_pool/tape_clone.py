"""各类对手的动作序列同源性:与其他对局(同队/异队)的最长公共前缀步数;完全相同的整局序列数。"""
import json, collections, statistics as st, hashlib
R=json.load(open("official_rows.json"))
seqs=collections.defaultdict(list)   # cls -> [(team, eid, seq)]
cache={}
def seq(eid,o):
    if eid not in cache: cache[eid]=json.load(open(f"roff/{eid}.json"))
    r=cache[eid]
    return [json.dumps(r["acts"][t][o],sort_keys=True) for t in range(1,len(r["acts"]))]
for r in R:
    o=1-r["seat"]; seqs[r["cls"]].append((r["team"],r["eid"],seq(r["eid"],o),tuple(r["shops"])))
def lcp(a,b):
    n=0
    for x,y in zip(a,b):
        if x!=y: break
        n+=1
    return n
print(f"{'类别':10s} {'对手局':>5s} {'队伍':>4s} | 最近邻公共前缀步(中位) 同队   异队   同商店异队 | 整局完全相同的对局")
for c,L in sorted(seqs.items(),key=lambda kv:-len(kv[1])):
    L=L[:160]
    same=[];diff=[];diffshop=[]
    for i,(t,e,s,sh) in enumerate(L):
        bs=0;bd=0;bds=0
        for j,(t2,e2,s2,sh2) in enumerate(L):
            if i==j or e==e2: continue
            v=lcp(s,s2)
            if t2==t: bs=max(bs,v)
            else:
                bd=max(bd,v)
                if sh2==sh: bds=max(bds,v)
        if any(t2==t and e2!=e for t2,e2,_,_ in L): same.append(bs)
        diff.append(bd); diffshop.append(bds)
    h=collections.Counter(hashlib.md5("".join(s).encode()).hexdigest() for _,_,s,_ in L)
    dup=sum(v for v in h.values() if v>1)
    med=lambda x: st.median(x) if x else "-"
    print(f"{c:10s} {len(L):5d} {len({t for t,_,_,_ in L}):4d} | {str(med(same)):>6s} {str(med(diff)):>6s} {str(med(diffshop)):>8s} | {dup}")
